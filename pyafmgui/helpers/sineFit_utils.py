from cProfile import label
import numpy as np
from lmfit import Model, Parameters
import matplotlib.pyplot as plt

def SineFunc(time, A, w, p, c):
    """
    Args:
        time: in seconds
        A: amplitude
        w: angular freq (freq * 2 * pi)
        p: phase
        c: offset
    Returns:
        A * np.sin(w*time + p) + c
    """
    return A * np.sin(w*time + p) + c

def SineFit(wave, time, p0):
    
    params = Parameters()
    params.add('A', value=p0[0])
    params.add('w', value=p0[1], vary=False)
    params.add('p', value=p0[2])
    params.add('c', value=p0[3])

    funcsine = Model(SineFunc)

    print(f'Sine parameter names: {funcsine.param_names}')
    print(f'Sine independent variables: {funcsine.independent_vars}')

    return funcsine.fit(wave, params, time=time)

def getGComplex(probe_model, tip_param, k, poisson, A_defl, A_ind, Avg_ind, dPhi, freq, bh0):
    print(probe_model, tip_param, k, poisson, A_defl, A_ind, Avg_ind, dPhi, freq, bh0)
    if probe_model == "cone":
        n = 2
        A_lambda = 2 / np.pi * np.tan(np.radians(tip_param))
        G = complex(k * A_defl / A_ind  * np.cos(dPhi),  k * A_defl / A_ind * np.sin(dPhi) -  2 * np.pi * freq * bh0 )
        return G  * ( ( 1 - poisson**2 ) / ( n * A_lambda * Avg_ind**(n-1) ) )
    elif probe_model == "paraboloid":
        n = 3/2
        A_lambda = 4 / 3 * np.sqrt(tip_param)
        G = complex( k * A_defl / A_ind  * np.cos(dPhi),  k * A_defl / A_ind * np.sin(dPhi) -  2 * np.pi * freq * bh0 )
        print(G)
        return G  * ( ( 1 - poisson**2 ) / ( n * A_lambda * Avg_ind**(n-1) )  )
    elif probe_model == "pyramid":
        n = 2
        A_lambda = 4 / ( 3 * np.sqrt(3) ) * np.tan(np.radians(tip_param))
        G = complex( k * A_defl / A_ind  * np.cos(dPhi ),  k * A_defl / A_ind * np.sin(dPhi) -  2 * np.pi * freq * bh0 )
        return G  * ( ( 1 - poisson**2 ) / ( n * A_lambda * Avg_ind**(n-1) )  )

def test_SineFit():
    N, amp, omega, phase, offset, noise = 500, 1., 2., .5, 4., 3
    tt = np.linspace(0, 10, N)
    tt2 = np.linspace(0, 10, 10*N)
    yy = amp*np.sin(omega*tt + phase) + offset
    yynoise = yy + noise*(np.random.random(len(tt))-0.5)
    guess_freq = omega/(2.*np.pi)
    guess_amp = np.std(yy) * 2.**0.5
    guess_offset = np.mean(yy)
    p0 = np.array([guess_amp, 2.*np.pi*guess_freq, 0., guess_offset])
    res = SineFit(yynoise, tt, p0)
    plt.plot(tt, yynoise, label="Raw data")
    plt.plot(tt, res.best_fit, label="Sine Fit")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    test_SineFit()