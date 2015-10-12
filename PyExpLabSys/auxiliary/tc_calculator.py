def TC_Calculator(V, No=1, tctype='K'):
    if tctype == 'K':
        coef = []
        coef.append( 0.0)
        coef.append( 0.0 * 1.0)
        coef.append( 2.5928 * 10)
        coef.append( -7.602961 * 10**-1)
        coef.append( 4.637791 * 10**-2)
        coef.append( -2.165394 * 10**-2)
        coef.append( 6.048144 * 10**-5)
        coef.append( -7.293422 * 10**-7)
    else:
        return None

    V = V/No
    T = 0.0
    for i, c in enumerate(coef):
        T += c * V**i
    return T
