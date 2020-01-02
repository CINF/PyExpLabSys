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
                    cutoff_big=3, mu=(0,0), sigma=(2,4), A=(3,0.3), radius_aperture=2.25):

    # Low intensity region
    D = (X - center_small[0])**2 + (Y - center_small[1])**2
    Z = gaussian(np.sqrt(D), mu[1], sigma[1])*A[1]
    # High intensity region
    D = (X - center_big[0])**2 + (Y - center_big[1])**2
    index_high = [D <= cutoff_big**2]
    Z[index_high] = gaussian(np.sqrt(D[index_high]), mu[0], sigma[0])*A[0]
    # Aperture mask cutoff
    Z[ X**2 + Y**2 > radius_aperture**2 ] = 0
    return Z

# Integrate beam profile and plot it
def normalize_beam_profile(num=100, moodkwargs=dict()):
    X, dx = np.linspace(-3, 3, num, retstep=True)
    Y, dy = np.linspace(-3, 3, num, retstep=True)
    X, Y = np.meshgrid(X, Y)

    Z = skewed_gaussian(X, Y, **moodkwargs)
    #area = np.sum(Z)*dx*dy
    radius_aperture = moodkwargs['radius_aperture']
    area = np.average(Z[X**2 + Y**2 <= radius_aperture**2])

    fig3 = plt.figure(3)
    bp_ax = fig3.gca(projection='3d')
    bp_ax.plot_wireframe(X, Y, Z/area*10)
    return area, bp_ax

# Print out Z profile in ascii format
def print_ascii(profile, output_name='default_ascii_output'):
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

if __name__ == '__main__':

    import sys
    import numpy as np
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import mpl_toolkits.mplot3d.art3d as art3d
    from matplotlib import cm
    from matplotlib.patches import Circle

    ###########################################################################
    ### User constants ###
    # Radius of aperture - defining spot size (usually always 2.25
    radius_ap = 2.25
    # Radius of mask - desired deposition area / sample area
    r_mask = 2.5
    # Center of mask - change to "offset/misalign" sample (mm)
    center_mask = (0, 0)

    # Type of sample outline - comment/uncomment
    mask_type = 'circle'
    #mask_type = 'square' # in this case, some output may still be hardcoded for "circle"

    NP_diameter = 5 # (nm) nanoparticle size
    charge = 0.14985 # pmol clusters (output from CalculateCoverage plugin)
    # 0.067 pmol corresponds to 5% 5 nm NPs on a 5mm circular area (non-rastered)

    # output options
    ascii = 0
    plot = 1
    ###########################################################################

    if len(sys.argv) > 0:
        filename = sys.argv[1]
    else:
        filename = 'test_pattern.pattern'

    if len(sys.argv) > 2:
        mood = sys.argv[2]
    else:
        mood = 'bad'

    if mood == 'bad':
        moodkwargs = dict(
            center_big = (-3, -3),
            center_small = (-3,0),
            cutoff_big = 3,
            mu = (0, 0),
            sigma = (2, 4),
            A = (3, 0.3),
            radius_aperture = radius_ap,
            )
    elif mood == 'good':
        moodkwargs = dict(
            center_big = (0,0),
            center_small = (0,0),
            cutoff_big = 0,
            mu = (0, 0),
            sigma = (2, 5),
            A = (0, 1),
            radius_aperture = radius_ap,
            )

    # Import pattern
    pattern, data = load_pattern(filename)

    fig = plt.figure(1)
    projection = fig.gca(projection='3d')

    fig2 = plt.figure(2)
    sketch = fig2.add_subplot(111)


    # Data
    num = 200
    X = np.linspace(-1, 1, num)*10 # mm
    Y = np.linspace(-1, 1, num)*10 # mm
    cell_length = X[1] - X[0]
    cell_area = cell_length**2
    print('Cell size = {} mm^2'.format(cell_area))
    #dx, dy = dx*10, dy*10
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
    hardcoded_delay = 0.1 #s
    (z, y) = start_point
    for (axis, dist) in pattern:
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
    print('Starting simulation...')
    print('Note a hardcoded delay of {} seconds is added every time a motion'.format(hardcoded_delay))
    print('changes direction due to delay in communication with the motors.\n')

    area, bp_ax = normalize_beam_profile(moodkwargs=moodkwargs)

    # Main loop
    total_time = 0
    previous_point = None
    for (coordinates, dt) in center_list:
        #print(coordinates)
        for c in coordinates:
            #print(c, dt)
            total_time += dt
            # Sketch raster pattern
            circle = Circle(xy=c, radius=radius_ap, facecolor='b', linewidth=0, alpha=0.05)
            sketch.add_patch(circle)
            if previous_point:
                sketch.plot([previous_point[0], c[0]], [previous_point[1], c[1]], 'ko-', 
                    markersize=4,
                    markerfacecolor='r',
                    markeredgecolor='k',
                    )
            previous_point = c
            Z += skewed_gaussian(X - c[0], Y - c[1], **moodkwargs)#/area * dt/3600.

    print('Time for 1 round: {:.1f} s = {:.1f} min'.format(total_time, total_time/60))
    # Sketch deposition area
    sketch.plot(x_mask, y_mask, 'k-', linewidth=2)
    try:
        plt.axis('equal')
    except NotImplementedError:
        pass
    sketch.axis([-10, 10, -10, 10])

    # Renormalize to match with coverage:
    Z = Z/np.sum(Z)
    Z = Z * charge*1e-12*6.022e23 * np.pi*(NP_diameter*1e-6/2)**2/cell_area*100
    maximum = np.max(Z)
    average = np.average(Z[ (X + center_mask[0])**2 + (Y + center_mask[1])**2 <= r_mask**2 ])
    std = np.std(Z[ (X + center_mask[0])**2 + (Y + center_mask[1])**2 <= r_mask**2 ])
    nominal_coverage = charge*1e-12*6.022e23 * np.pi * (NP_diameter*1e-6/2)**2 / (np.pi * r_mask**2) * 100
    correction_factor = np.sqrt(nominal_coverage/average)
    print('')
    print('Average inside dep area (total): {:.3f} % ± {:.3f} % (2*std)\n'.format(average, 2*std))
    print('Maximum local coverage: {:.3f} %'.format(maximum))
    print('Minimum local coverage: {:.3f} %'.format(np.min(Z[index_mask])))

    print('Nominal coverage: {:.3f} %'.format(nominal_coverage))
    print('"Nominal coverage" assumes all the charge is distributed evenly across the sample')
    print('i.e. within "r_mask". This gives a correction factor for the coverage calculator plugin')
    print('Correction factor: {}'.format(correction_factor))
    print('leading to an effective "APERTURE_DIAMETER" = {}'.format(correction_factor*2*r_mask))

    # Make 3D plot of surface
    for i in range(3):
        projection.plot(x_mask, y_mask, z_mask + maximum*float(i)/3, linewidth=2, color='k', alpha=0.6)
    projection.plot(x_mask, y_mask, z_mask + average, linewidth=2, color='g')
    projection.set_zlabel('Relative Coverage (%)')
    i =  X**2 + Y**2 <= r_mask**2
    j1 = np.array([X**2 + Y**2 > r_mask**2])
    j2 = np.array([X**2 + Y**2 < 6**2])
    j = j1[0] == j2[0]
    surf3 = projection.plot_surface(X, Y, Z, cmap=cm.hot, vmin=average-3*std, vmax=average+3*std)
    for ax in [sketch, projection]:
        ax.set_xlabel('x (mm)')
        ax.set_ylabel('y (mm)')
        ax.set_title(filename)
    fig.colorbar(surf3)

    # Make contour plot of coverage
    plt.figure()
    plt.contourf(X, Y, Z)
    plt.colorbar()
    plt.plot(x_mask, y_mask, 'k-', linewidth=2)
    try:
        plt.axis('equal')
    except NotImplementedError:
        pass

    total_intensity = np.sum(Z)
    in_mask_intensity = np.sum(Z[index_mask])
    print('Percent of charge within mask: {:.3f} %'.format(in_mask_intensity/total_intensity*100))
    if ascii:
        output_name = filename.split('.')[0] + '_' + mood
        print_ascii(Z, output_name)
    if plot:
        plt.show()

