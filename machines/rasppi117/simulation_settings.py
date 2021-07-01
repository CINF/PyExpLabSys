###########################################################################
### User constants ###          
# Radius of aperture - defining spot size (usually always 2.25)
radius_ap = 2.25
# Radius of mask - desired deposition area / sample area
#r_mask = 2.25
r_mask = 2.5
#r_mask = 4.0
# Center of mask - change to "offset/misalign" sample (mm)
center_mask = (0, 0)

# Type of sample outline - comment/uncomment
#mask_type = 'circle'
mask_type = 'square' # in this case, some output may still be hardcoded for "circle"

NP_diameter = 5 # (nm) nanoparticle size
charge = 0.05985 # pmol clusters (output from CalculateCoverage plugin)
charge = 0.479232370611
charge = 5.1095
charge = 0.2997971108113286 # Good Game 45
#charge = 0.06725*14.4
# 0.06725 pmol corresponds to 5% 5 nm NPs on a 5mm circular area (non-rastered)
experiment = dict()
experiment['match'] = False
experiment['id'] = 1337
# Enabling the "match experiment" further requires access to SurfCat database
# and the script "integrate_deposition_current.py" from "Data Treatment" on Ejler@github

# Define your own beam profile by adding two gaussian functions (big and small) with a cutoff
# on the big one.
if False:
    print('Using custom beam profile from file')
    moodkwargs = dict(
        name = 'Intense spot corner',
        center_big =   (-2, -2.2),
        center_small = (-3, 0),
        cutoff_big =    3,
        mu =           (0, 0),
        sigma =        (0.51, 5),
        A =            (2.3, 0),
    )
if False:
    print('Using custom beam profile from file')
    moodkwargs = dict(
        name = 'Intense spot bottom',
        center_big =   (0, -2.2),
        center_small = (-3, 0),
        cutoff_big =    3,
        mu =           (0, 0),
        sigma =        (0.51, 5),
        A =            (2.3, 0),
    )
if True:
    print('Using custom beam profile from file')
    moodkwargs = dict(
        name = 'Intense spot center',
        center_big =   (0, 0),
        center_small = (-3, 0),
        cutoff_big =    3,
        mu =           (0, 0),
        sigma =        (0.21, 5),
        A =            (2.3, 0),
    )

# output options                
print_ascii = 0
plot = 1
###########################################################################            
