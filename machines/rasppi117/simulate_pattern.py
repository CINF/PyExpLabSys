import time
def gaussian(x, mu, sigma):
    return np.exp(-np.power(x - mu, 2.)/(2*np.power(sigma, 2.)))

def load_pattern(filename):
    """Load data from a xxxx.pattern file"""
    data = {
        'step_size': None,
        'speed': None,
        'offset': [],
        'error': False
        }
    pattern = []

    f = open(filename, 'r')
    while True:
        line = f.readline()
        if line.startswith('#'):
            # Skip comments
            continue
        if len(line) == 0:
            raise ValueError('Empty line encountered. End FILE with \"<<<END>>>\".')

        # Read data lines
        if line.startswith('<<<DATA>>>'):
            for i in range(2):
                line = f.readline()
                if line.startswith('step_size'):
                    data['step_size'] = float(line.split('=')[1])
                elif line.startswith('speed'):
                    data['speed'] = float(line.split('=')[1])

        # Read pattern
        if line.startswith('<<<PATTERN>>>'):
            while True:
                line = f.readline()
                if line.startswith('<<<END>>>'):
                    z, y = 0, 0
                    for (axis, dist) in pattern:
                        if axis == 'Z':
                            z += dist
                        elif axis == 'Y':
                            y += dist
                    if round(z) != 0 or round(y) != 0:
                        print('Error. Pattern doesn\'t add up to zero ({}, {}).'.format(z, y))
                        data['error'] = True
                    return pattern, data
                elif len(line) == 0:
                    raise ValueError('Empty line encountered during pattern. \
Mark end of FILE/PATTERN with \"<<<END>>>\".')
                elif '-->' in line:
                    newline = line.split('->')[1]
                    data['offset'].append((newline.lstrip(' ')[0], float(newline.split(':')[1])))

                # Repeat pattern
                elif '{' in line:
                    multipattern = []
                    while len(line) > 0:
                        line = f.readline()
                        if '}' in line:
                            multiplier = int(line.split('*')[1])
                            break
                        else:
                            newline = line.lstrip(' ').split(':')
                            multipattern.append((newline[0], float(newline[1])))
                    else:
                        raise ValueError('Multiplier section not finished')
                    for i in range(multiplier):
                        for elements in multipattern:
                            pattern.append(elements)
                else:
                    newline = line.lstrip(' ').split(':')
                    pattern.append((newline[0], float(newline[1])))
            

# Define beam profile
def skewed_gaussian(X, Y, center_big=(-3,-3), center_small=(-3,0),
                    cutoff_big=3, mu=(0,0), sigma=(2,4), A=(3,0.3), radius_aperture=2.25, **kwargs):

    # Low intensity region
    D = (X - center_small[0])**2 + (Y - center_small[1])**2
    Z = gaussian(np.sqrt(D), mu[1], sigma[1])*A[1]

    # High intensity region
    D = (X - center_big[0])**2 + (Y - center_big[1])**2
    Z += gaussian(np.sqrt(D), mu[0], sigma[0])*A[0]

    # Aperture mask cutoff
    Z[ X**2 + Y**2 > radius_aperture**2 ] = 0
    return Z

# Integrate beam profile and plot it
def normalize_beam_profile(num=100, moodkwargs=dict()):
    radius_aperture = moodkwargs['radius_aperture']

    # Create fine grid and apply beam profile
    X, dx = np.linspace(-radius_aperture, radius_aperture, int(2*radius_aperture+1)*100, retstep=True)
    Y, dy = np.linspace(-radius_aperture, radius_aperture, int(2*radius_aperture+1)*100, retstep=True)
    X, Y = np.meshgrid(X, Y)
    Z = skewed_gaussian(X, Y, **moodkwargs)

    # Get average value inside the aperture cutoff radius
    area = np.average(Z[X**2 + Y**2 <= radius_aperture**2])

    # Plot and return normalized
    fig3 = plt.figure(3)
    bp_ax = fig3.gca(projection='3d') ### DEPRECATED
    bp_ax.plot_wireframe(X, Y, Z/area*10)
    return area, bp_ax

# Print out Z profile in ascii format
def print_ascii_output(profile, output_name='default_ascii_output'):
    if output_name.lower()[-4:] != '.txt':
        output_name += '.txt'
    f = open(output_name, 'w')
    for i in range(len(profile)):
        string = ''
        for j in range(len(profile[i])):
            string += str(profile[i, j]) + '\t'
        string = string[:-1] + '\n'
        f.write(string)
    f.close()

color_dict = {'black': '\033[30m', 'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m',
    'blue': '\033[34m', 'magenta': '\033[35m', 'cyan': '\033[36m', 'white': '\033[37m',
    'bright black': '\033[90m', 'bright red': '\033[91m', 'bright green': '\033[92m', 'bright yellow': '\033[93m',
    'bright blue': '\033[94m', 'bright magenta': '\033[95m', 'bright cyan': '\033[96m', 'bright white': '\033[97m'}
def color(text='', ctext='red'):
    return color_dict[ctext] + text + color_dict['bright white']

if __name__ == '__main__':
    print('-'*40)
    import sys
    from pathlib import Path
    import numpy as np
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import mpl_toolkits.mplot3d.art3d as art3d
    from matplotlib import cm
    from matplotlib.patches import Circle

    # Interpret command-line options
    if len(sys.argv) > 0:
        filename = sys.argv[1]
    else:
        filename = 'test_pattern.pattern'
        mood = 'bad'
    if filename.lower() == 'stationary':
        stationary = True
    else:
        stationary = False
    print('Raster pattern file: ', filename)

    if len(sys.argv) > 2:
        mood = sys.argv[2]
    else:
        mood = 'bad'

    if mood == 'bad':
        moodkwargs = dict(
            name = 'bad',
            center_big = (-2, -2.2),
            center_small = (-3,0),
            cutoff_big = 3,
            mu = (0, 0),
            sigma = (1, 5),
            A = (2.3, 0.3),
            #radius_aperture = radius_ap,
            )
    elif mood == 'good':
        moodkwargs = dict(
            name = 'good',
            center_big = (0,0),
            center_small = (0,0),
            cutoff_big = 0,
            mu = (0, 0),
            sigma = (2, 5),
            A = (0, 1),
            #radius_aperture = radius_ap,
            )

    # Note that the following constants will be used to extract useful numbers from the simulation
    # Default example values are hardcoded here, but should be overwritten in "simulation_settings.py" file.
    radius_ap, r_mask = 2.25, 2.5 # radius aperture, radius sample
    center_mask, mask_type = (0, 0), 'circle' # sample offset (mm), geometry of sample
    NP_diameter, charge = 5, 0.14985 # nm, pmol clusters
    print_ascii, plot = 0, 1 # BOOL: print result in ascii file, plot result in matplotlib figures

    # Read user constants from settings file
    print('\nOverwriting defaults with values from user file..')
    try:
        from simulation_settings import *
    except ImportError:
        print(color('Custom settings file missing - using hardcoded defaults!'))
    moodkwargs['radius_aperture'] = radius_ap
    print(color('Settings used:', 'cyan'))
    print('\tAperture radius: {} mm'.format(radius_ap))
    print('\tSample radius: {} mm'.format(r_mask))
    print('\tSample offset: {} mm'.format(center_mask))
    print('\tSample geometry: {}'.format(mask_type))
    print('\tNanoparticle diameter: {} nm'.format(NP_diameter))
    print('\tNumber of nanoparticles: {} pmol'.format(charge))
    print('\tRastering: {}'.format(not stationary))
    print('\tBeam profile: {}'.format(moodkwargs['name']))
    print('\tPrinting ascii {}'.format(bool(print_ascii)))
    print('\tPlotting {}'.format(bool(plot)))

    # Import pattern
    if not stationary:
        pattern, data = load_pattern(filename)

    fig = plt.figure(1)
    projection = fig.gca(projection='3d') ### DEPRECATED

    fig2 = plt.figure(2)
    sketch = fig2.add_subplot(111)


    # Data
    num = 1500
    X = np.linspace(-1, 1, num)*10 # mm
    Y = np.linspace(-1, 1, num)*10 # mm
    cell_length = X[1] - X[0]
    cell_area = cell_length**2
    print('Cell size = {} mm^2'.format(cell_area))
    print('Cell length = {} mm'.format(cell_length))
    X, Y = np.meshgrid(X, Y)

    Z = np.zeros((len(X), len(Y)))

    if mask_type == 'square':
        x_mask = np.array([-r_mask,-r_mask,r_mask,r_mask,-r_mask]) + center_mask[0]
        y_mask = np.array([-r_mask,r_mask,r_mask,-r_mask,-r_mask]) + center_mask[1]
        z_mask = np.zeros(len(x_mask))
    elif mask_type == 'circle':
        theta = np.linspace(0, 2*np.pi, 100)
        x_mask = r_mask * np.cos(theta) + center_mask[0]
        y_mask = r_mask * np.sin(theta) + center_mask[1]
        z_mask = x_mask*0
    if mask_type == 'square':
        index_mask = np.logical_and(X + center_mask[0] < r_mask, X + center_mask[0] > -r_mask)
        index_mask = np.logical_and(index_mask, Y + center_mask[1] < r_mask)
        index_mask = np.logical_and(index_mask, Y + center_mask[1] > -r_mask)
    elif mask_type == 'circle':
        index_mask = (X + center_mask[0])**2 + (Y + center_mask[1])**2 < r_mask**2

    total_dist = 0
    total_turns = 0
    hardcoded_delay = 0.2 #s
    if not stationary:
        # Load offset and data
        speed = data['speed'] # mm/s
        z, y = 0, 0
        for (axis, dist) in data['offset']:
            if axis == 'Z':
                z += dist
            elif axis == 'Y':
                y += dist
            else:
                raise NameError('Unknown axis identifier encountered in offset: {}'.format(axis))
        start_point = (z*data['step_size'], y*data['step_size']) # coordinates for start algorithm

        # Insert centers of raster pattern
        center_list = []
        (z, y) = start_point
        for (axis, dist) in pattern:
            total_dist += abs(dist)*data['step_size']
            total_turns += 1
            if axis == 'Z':
                z0 = z
                z += dist*data['step_size']
                step_num = int(abs(z-z0)/cell_length)
                if step_num < 2:
                    step_num = 2
                # Include endpoint on purpose (motor stops briefly)
                centers, step = np.linspace(z0, z, step_num, retstep=True)
                centers = centers[1:] # don't count start coordinate
                center_list.append((zip(centers, np.ones(len(centers))*y), abs(step/speed)))
                center_list.append(([(centers[-1], y)], hardcoded_delay))
            elif axis == 'Y':
                y0 = y
                y += dist*data['step_size']
                step_num = int(abs(y-y0)/cell_length)
                if step_num < 2:
                    step_num = 2
                # Include endpoint on purpose (motor stops briefly)
                centers, step = np.linspace(y0, y, step_num, retstep=True)
                centers = centers[1:] # don't count start coordinate
                center_list.append((zip(np.ones(len(centers))*z, centers), abs(step/speed)))
                center_list.append(([(z, centers[-1])], hardcoded_delay))
            else:
                raise NameError('Unknown axis identifier encountered in pattern: {}'.format(axis))

        # Use index as criteria
        i_endpoints = []
        x0, y0 = start_point
        # Find index of center
        r2 = (X-x0)**2 + (Y-y0)**2
        r_min = np.min(r2)
        ic = np.where(r2 == r_min)
        c0, c1 = ic[0][0], ic[1][0]
        i_endpoints.append([c0, c1])
        # Loop again
        for (axis, dist) in pattern:
            if axis == 'Z':
                x0 += dist*data['step_size']
            elif axis == 'Y':
                y0 += dist*data['step_size']
            # Find index of center
            r2 = (X-x0)**2 + (Y-y0)**2
            r_min = np.min(r2)
            ic = np.where(r2 == r_min)
            c0, c1 = ic[0][0], ic[1][0]
            i_endpoints.append([c0, c1])
        # Find weight of endpoint waiting
        tw = cell_length/data['speed'] # time to cross one cell
        weight = hardcoded_delay / tw # weight of waiting 0.1s between axes relative to pixel size and speed

        print(color('Starting simulation...', 'cyan'))
        print(color('***') + ' Note a hardcoded delay of ' + color('{} seconds'.format(hardcoded_delay), 'cyan') + ' is added every time a motion')
        print('changes direction due to delay in communication with the motors. ' + color('***') + '\n')

    #for col in color_dict.keys():
    #    print(color(col, col))
    
    plt.close('all')
    area, bp_ax = normalize_beam_profile(moodkwargs=moodkwargs)
    #plt.show()
    #1/0

    # Save beam profile
    import pickle
    beam = skewed_gaussian(X, Y, **moodkwargs)
    path = Path.cwd() / 'data_dumps'
    if not path.exists():
        print('Creating folder: {}'.format(path))
        path.mkdir()
    
    filename_beam = path / 'beam_profile_{}.pickle'.format(moodkwargs['name'])
    with open(filename_beam, 'wb') as f:
        pickle.dump((X, Y, beam), f, pickle.HIGHEST_PROTOCOL)
    # Find index delimiters of beam profile
    m = np.where(beam > 0, True, False)
    x_min, x_max = min(X[m]), max(X[m])
    ix0 = (np.where(X[0, :] == x_min)[0] - 1)[0]
    ix1 = (np.where(X[0, :] == x_max)[0] + 1)[0]
    y_min, y_max = min(Y[m]), max(Y[m])
    iy0 = (np.where(Y[:, 0] == y_min)[0] - 1)[0]
    iy1 = (np.where(Y[:, 0] == y_max)[0] + 1)[0]

    # Crop beam
    beam = beam[ix0:ix1,iy0:iy1]
    dix = int((ix1 - ix0)/2)
    diy = int((iy1 - iy0)/2)
    print(dix, diy)
    print('Beam is represented by a {}x{} grid'.format(*beam.shape))
    if stationary:
        Z = skewed_gaussian(X, Y, **moodkwargs)
    else:
        # Main loop
        total_time = 0
        previous_point = None
        counter = 0
        i = 0
        """
        for (coordinates, dt) in center_list:
            print('Progress: {:.3f} %       '.format(counter/len(center_list)*100), end='\r')
            counter += 1
            for c in coordinates:
                i += 1
                total_time += dt
                # Sketch raster pattern
                #circle = Circle(xy=c, radius=radius_ap, facecolor='b', linewidth=0, alpha=0.05)
                #sketch.add_patch(circle)
                #if previous_point:
                #    sketch.plot([previous_point[0], c[0]], [previous_point[1], c[1]], 'ko-', 
                #        markersize=4,
                #        markerfacecolor='r',
                #        markeredgecolor='k',
                #    )
                previous_point = c
                #Z += skewed_gaussian(X - c[0], Y - c[1], **moodkwargs)

                # Find index of center
                r2 = (X-c[0])**2 + (Y-c[1])**2
                r_min = np.min(r2)
                ic = np.where(r2 == r_min)
                c0, c1 = ic[0][0], ic[1][0]
                #print((X[c0, c1], Y[c0, c1]), c)
                #1/0
                Z[c0 - dix:c0 + dix+1,c1-diy:c1+diy+1] += beam
        print(i)
        """
        # For image show, pixels vs index goes Z[yy, xx]
        for i, (c0, c1) in enumerate(i_endpoints):
            if i == 0:
                previous = (c0, c1)
                continue
            # Create pixelated path
            #print('--- ', previous[0], previous[1], '-->', c0, c1, ' ---')
            if c0 == previous[0]: # Walking along Y:
                if c1 > previous[1]: # go forwards
                    for cy in range(previous[1] + 1, c1 + 1): # dismiss start, include end
                        #print(cy)
                        Z[c0 - dix:c0 + dix+1,cy-diy:cy+diy+1] += beam
                else: # create a backwards list
                    for cy in range(previous[1] - 1, c1 - 1, -1): # dismiss start, include end
                        #print(cy)
                        Z[c0 - dix:c0 + dix+1,cy-diy:cy+diy+1] += beam
            elif c1 == previous[1]: # Walking along Z:
                if c0 > previous[0]: # go forwards
                    for cx in range(previous[0] + 1, c0 + 1): # dismiss start, include end
                        #print(cx)
                        Z[cx - dix:cx + dix+1,c1-diy:c1+diy+1] += beam
                else: # go backwards
                    for cx in range(previous[0] - 1, c0 - 1, -1): # dismiss start, include end
                        #print(cx)
                        Z[cx - dix:cx + dix+1,c1-diy:c1+diy+1] += beam
            previous = (c0, c1)
            print('Progress: {:.3f} %       '.format(i/len(i_endpoints)*100), end='\r')
            # Add weighted beam at endpoints (0.1 s delay)
            Z[c0 - dix:c0 + dix+1,c1-diy:c1+diy+1] += beam*weight

    # Sketch deposition area
    sketch.plot(x_mask, y_mask, 'k-', linewidth=2)
    try:
        plt.axis('equal')
    except NotImplementedError:
        pass
    sketch.axis([-10, 10, -10, 10])

    # Renormalize and scale to match with coverage:
    Z = Z/np.sum(Z)
    Z = Z * charge*1e-12*6.022e23 * np.pi*(NP_diameter*1e-6/2)**2/cell_area*100

    # Save output
    filename_sim = 'data_dumps/sim_{}_{}.pickle'.format(moodkwargs['name'], filename.rstrip('.pattern'))
    with open(filename_sim, 'wb') as f:
        pickle.dump((X, Y, Z), f, pickle.HIGHEST_PROTOCOL)

    # Get statistical information about sample area
    maximum = np.max(Z[index_mask])
    average = np.average(Z[index_mask])
    std = np.std(Z[index_mask])

    # Correlate rastered settings with stationary values to get a correlation factor:
    #
    # "nominal coverage" here refers to the coverage calculated from the supplied charge through the aperture
    # while the sample is stationary. I.e., if you use the actual aperture diameter in the coverage calculator
    # plugin script, the coverage that is output would be the "nominal coverage"
    # nominal_coverage = (number of particles) * (cross-sectional area per particle) / (beam profile area) * 100
    nominal_coverage = (charge*1e-12*6.022e23) * (np.pi * (NP_diameter*1e-6/2)**2) / (np.pi * radius_ap**2) * 100
    # We then want to find the proportionality between the actual and effective aperture diameter
    correction_factor = np.sqrt(nominal_coverage/average)
    # From the coverage calculator plugin, the "aperture diameter" translates to sample or deposition area.
    # Therefore, r_mask is used for the effective aperture diameter and not radius_ap.
    ap_dia_eff = correction_factor*2*radius_ap#r_mask
    total_intensity = np.sum(Z)
    in_mask_intensity = np.sum(Z[index_mask])

    # Print results to screen
    print('\r                      ', end='\r')
    msg = '\tDistance per raster cycle: {} mm ({} turns)'.format(round(total_dist, 1), total_turns)
    print(msg)
    if not stationary:
        total_time = total_dist/data['speed'] + 0.1*total_turns
        msg = '\tTime raster cycle: ' + color('{:.1f} s'.format(total_time), 'green')
        msg += ' = ' + color('{:.1f} min'.format(total_time/60), 'green')
        print(msg)
    print('')
    msg = '\tAverage coverage on sample: '
    msg += color('{:.3f} % ± {:.3f} %'.format(average, 2*std), 'green') + ' (2*std)\n'
    print(msg)
    print('\tMaximum local sample coverage: {:.3f} %'.format(maximum))
    print('\tMinimum local sample coverage: {:.3f} %'.format(np.min(Z[index_mask])))
    print('')
    print('\tNominal coverage: {:.3f} %'.format(nominal_coverage))
    print('\tPercent of charge within mask: {:.3f} %'.format(in_mask_intensity/total_intensity*100))
    print(color('"Nominal coverage"', 'cyan') + ' assumes the deposition is stationary and all the particles are')
    print('distributed evenly across the sample, i.e. within "r_mask". This gives a correction factor for the')
    print('coverage calculator plugin: {}.'.format(correction_factor))
    print('This gives an ' + color('effective "APERTURE_DIAMETER" = {}'.format(ap_dia_eff), 'green'))
    msg = '(use this number in the coverage calculator plugin to take the rastering into account and have the\n' \
          'output coverage be representative of the final coverage of the sample.)'
    print(color(msg, 'cyan'))
    print('')


    # Make 3D plot of surface
    for i in range(3):
        projection.plot(x_mask, y_mask, z_mask + maximum*float(i)/3, linewidth=2, color='k', alpha=0.6)
    projection.plot(x_mask, y_mask, z_mask + average, linewidth=2, color='g')
    projection.set_zlabel('Relative Coverage (%)')
    surf3 = projection.plot_surface(X, Y, Z, cmap=cm.hot, vmin=average-3*std, vmax=average+3*std)
    for ax in [sketch, projection]:
        ax.set_xlabel('x (mm)')
        ax.set_ylabel('y (mm)')
        ax.set_title(filename)
    #fig.colorbar(surf3)

    # Make contour plot of coverage
    plt.figure()
    plt.imshow(Z, aspect='equal', origin='lower', extent=(-10, 10, -10, 10), cmap=cm.nipy_spectral)
    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Coverage ($\%$)')
    plt.plot(x_mask, y_mask, 'k', linewidth=2, linestyle='dashed')
    plt.xlabel('mm')
    plt.ylabel('mm')
    try:
        plt.axis('equal')
    except NotImplementedError:
        pass
    print('-'*40)
    if print_ascii:
        output_name = filename.split('.')[0] + '_' + mood
        print_ascii_output(Z, output_name)
    if plot:
        plt.show()

