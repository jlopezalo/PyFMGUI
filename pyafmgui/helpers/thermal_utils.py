
import os
import numpy as np
import pandas as pd
import re
import requests
import xml.etree.ElementTree as etree
import matplotlib.pyplot as plt
from scipy.special import kv
from lmfit import Model, Parameters
import pyafmgui.const as cts

def SaderGCI_CalculateK(UserName, Password, LeverNumber, Frequency, QFactor):
    payload = '''<?xml version="1.0" encoding="UTF-8" ?>
    <saderrequest>
        <username>'''+UserName+'''</username>
        <password>'''+Password+'''</password>
        <operation>UPLOAD</operation>
        <cantilever>
            <id>data_'''+str(LeverNumber)+'''</id>
            <frequency>'''+str(Frequency)+'''</frequency>
            <quality>'''+str(QFactor)+'''</quality>
        </cantilever>
    </saderrequest>'''
    headers = {'user-agent': cts.SADER_API_version, 'Content-type': cts.SADER_API_type}
    r = requests.post(cts.SADER_API_url, data=payload, headers=headers)
    doc = etree.fromstring(r.content)
    if (doc.find('./status/code').text == 'OK'):
        print ("Sader GCI Spring Constant = "+doc.find('./cantilever/k_sader').text+', 95% C.I. Error = '+doc.find('./cantilever/percent').text+'% from '+doc.find('./cantilever/samples').text+' samples.')
        # Added return statement for the GCI Spring Constant
        return float(doc.find('./cantilever/k_sader').text)

def get_K_Classic(fR, Q, A1, temperature):
    BoltzmannConst = 1.38065e-23
    abs_temp = temperature + 273.15
    energy = BoltzmannConst * abs_temp
    return energy / ( np.pi / 2 * fR * np.abs(Q) * A1**2) 

def reynolds_number_rect(rho, eta, omega, b):
    # Input:
        # rho:   density of surrounding fluid {kg/m^3}
        # eta:   viscosity of surrounding fluid {kg/m.s}
        # omega: cantilever-fluid resonant frequency
        # b:     width of the cantilever {m}
    # Output
        # Re:    Reynolds Number {unitless}
    return 0.250 * rho * omega * b**2 / eta

def reynolds_number_V(rho, eta, omega, d):
    # Input:
        # rho:   density of surrounding fluid {kg/m^3}
        # eta:   viscosity of surrounding fluid {kg/m.s}
        # omega: cantilever-fluid resonant frequency
        # d:     width of the legs of cantilever {m}
    # Output
        # Re:    Reynolds Number {unitless}
    return rho * omega * d**2 / eta

def omega(Re):
    tau = np.log10(Re)
    omega_real = (0.91324 - 0.48274 * tau + 0.46842 * tau**2 - 0.12886 * tau**3 \
        + 0.044055 * tau**4 - 0.0035117 * tau**5 + 0.00069085 * tau**6) \
        * (1 - 0.56964 * tau + 0.48690 * tau**2 - 0.13444 * tau**3 \
        + 0.045155 *  tau**4 - 0.0035862 * tau**5 \
        + 0.00069085 * tau**6)**-1
    omega_imag = (-0.024134 - 0.029256 * tau + 0.016294 * tau**2 \
        - 0.00010961 * tau**3 + 0.000064577 * tau**4 \
        - 0.000044510 * tau**5 )*( 1 - 0.59702 * tau + 0.55182 * tau**2 \
        - 0.18357 * tau**3 + 0.079156 * tau**4 - 0.014369 * tau**5 \
        + 0.0028361 * tau**6 )**-1
    return np.complex(omega_real, omega_imag)

def gamma_circ(Re):
    K1 = kv(1, -1j*np.sqrt(1j*Re))
    K0 = kv(0, -1j*np.sqrt(1j*Re))
    return 1 + 4*1j*K1 / (np.sqrt(1j*Re)*K0)

def gamma_rect(Re):
    return omega(Re) * gamma_circ(Re)

def force_constant(rho, eta, b, L, d, Q, omega, cantType):
    if cantType == 'Rectangular':
        Re = reynolds_number_rect(rho, eta, omega, b)
    elif cantType == 'V Shape':
        Re = reynolds_number_V(rho, eta, omega, d)
    gamma_imag = np.imag(gamma_rect(Re))
    return 0.1906 * rho * b**2 * L * Q * gamma_imag * omega**2

def Stark_Chi_force_constant(b, L, d, A1, fR1, Q1, Tc, RH, medium, cantType, username="", pwd="", selectedCantCode=""):
    invOLS= 20*1e3 #in pm/V
    kB = 1.3807e-2*1e3 #in pNpm/K
    T=273+Tc
    xsqrA1=np.pi*A1**2*fR1/2/Q1
    if cantType == 'Rectangular':
        Chi1= 0.8174
    elif cantType == 'V Shape':
        Chi1= 0.764
    kcantiA=Chi1*kB*T/xsqrA1
    if medium == 'air':
        rho, eta = air_properties(Tc, RH)
    elif medium == 'water':
        rho = 1000
        eta = 0.9e-3
    k0 = force_constant(rho, eta, b, L, d, Q1, fR1*2*np.pi, cantType)
    if username != "" and pwd != "" and selectedCantCode != "":
        print(selectedCantCode)
        # SaderGCI_CalculateK( UserName, Password, LeverNumber, Frequency, QFactor)
        GCI_cant_springConst=SaderGCI_CalculateK(username, pwd, selectedCantCode, fR1/1e3, Q1)
    else:
        GCI_cant_springConst=np.NaN
    involsValue=invOLS*np.sqrt(kcantiA/k0)/1e3 
    invOLS_H=np.sqrt(2*kB*T/(np.pi*k0*(A1)**2/Q1*fR1))*invOLS/1e3*np.sqrt(Chi1)

    return k0, GCI_cant_springConst, involsValue, invOLS_H

def qsat(Ta,Pa=None):
    P_default = 1020     # default air pressure for Kinneret [mbars]
    if not Pa:
        Pa=P_default # pressure in mb
    ew = 6.1121*(1.0007+3.46e-6*Pa)*np.exp((17.502*Ta)/(240.97+Ta)) # in mb
    return 0.62197*(ew/(Pa-0.378*ew));                         # mb -> kg/kg

def air_dens(Ta, RH, Pa=None):
    eps_air = 0.62197    # molecular weight ratio (water/air)
    P_default = 1020     # default air pressure for Kinneret [mbars]
    CtoK = 273.16        # conversion factor for [C] to [K]
    gas_const_R = 287.04 # gas constant for dry air [J/kg/K]
    if not Pa:
        Pa = P_default
    o61 = 1/eps_air-1                 # 0.61 (moisture correction for temp.)
    Q = (0.01*RH)*qsat(Ta,Pa)     # specific humidity of air [kg/kg]
    T = Ta+CtoK                     # convert to K
    Tv = T*(1 + o61*Q)              # air virtual temperature
    return (100*Pa)/(gas_const_R*Tv);  # air density [kg/m^3]

def viscair(Ta):
    return 1.326e-5*(1 + 6.542e-3*Ta + 8.301e-6*Ta**2 - 4.84e-9*Ta**3)

def air_properties(T,RH):
    rho = air_dens(T,RH)
    eta = viscair(T)
    eta = eta*rho
    return rho, eta

def SHO_model(freq, Awhite, A, fR, Q):
    return Awhite**2 + A**2 * fR**4 / Q**2 * ((freq**2-fR**2)**2 + freq**2 * fR**2 / Q**2)**(-1)

def loadThermal(file_path):
    file_ext  = os.path.splitext(file_path)[1]
    if file_ext == ".tnd":
        header_rows = 23
        header_sep = '\n'
        data_sep = ' '
        file_header = pd.read_csv(file_path, header=None, nrows=header_rows)
        file_data = pd.read_csv(
            file_path, sep=data_sep, comment='#',
            names = ['Frequency', 'Vertical Deflection', 'average', 'fit-data'],
            engine='python')
        parameters = {}
        for value in file_header[0]:
            param_data = re.sub('[#:]', '', value).split(' ')
            # print(param_data)
            # if 'sensitivity' in param_data:
            #     parameters['sensitivity'] = float(param_data[2]) * 1e3 #pm/V
            if 'parameter.f' in param_data:
                parameters['resonancef'] = float(param_data[2]) * 1e3 #Hz
        invOLS= 20*1e3 # Why this value?
        # ampl = file_data['average'] * parameters['sensitivity'] ** 2
        ampl = file_data['average'] * invOLS ** 2
        freq = file_data['Frequency']
        return ampl.values, freq.values, parameters

def test_k_calibration():
    # To Do Make proper test
    # http://dx.doi.org/10.1063/1.1150021
    # http://experimentationlab.berkeley.edu/sites/default/files/AFMImages/Sader.pdf
    # force_constant(rho, eta, b, L, d, Q, omega
    print(force_constant(1.18, 1.86e-5, 29e-6, 397e-6, 0, 55.5, 17.36*10**3*2*3.1415, 'Rectangular'))
    print(force_constant(1.18, 1.86e-5, 29e-6, 197e-6, 0, 136.0, 69.87*10**3*2*3.1415, 'Rectangular'))
    print(force_constant(1.18, 1.86e-5, 29e-6,  97e-6, 0, 309.0, 278.7*10**3*2*3.1415, 'Rectangular'))

    print(force_constant(1.18, 1.86e-5, 20e-6, 203e-6, 0, 17.6, 10.31*10**3*2*3.1415, 'Rectangular'))
    print(force_constant(1.18, 1.86e-5, 20e-6, 160e-6, 0, 22.7, 15.61*10**3*2*3.1415, 'Rectangular'))
    print(force_constant(1.18, 1.86e-5, 20e-6, 128e-6, 0, 30.9, 24.03*10**3*2*3.1415, 'Rectangular'))
    print(force_constant(1.18, 1.86e-5, 20e-6, 105e-6, 0, 41.7, 36.85*10**3*2*3.1415, 'Rectangular'))
    print(force_constant(1.18, 1.86e-5, 20e-6,  77e-6, 0, 60.3, 64.26*10**3*2*3.1415, 'Rectangular'))

def ThermalFit(freq, ampl):

    params = Parameters()

    max_amp_indx = np.argmax(ampl)
    max_amp_freq = freq[max_amp_indx]
    max_amp = ampl[max_amp_indx]

    # Find p0
    Awhite_0 = np.sqrt((ampl[1]))
    A_0 = np.sqrt(max_amp)
    fR_0 = max_amp_freq
    Q_0 = 1
    
    # Define lower bounds
    Awhite_lb = np.sqrt(np.min(ampl)/100)
    A_lb = np.sqrt(np.max(ampl)/100)
    fR_lb = max_amp_freq/3
    Q_lb = 0.1

    # Define upper bounds
    Awhite_ub = np.sqrt(np.max(ampl)*10)
    A_ub = np.sqrt(np.max(ampl)*10) 
    fR_ub = max_amp_freq*3 
    Q_ub = 100

    # Define varying parameters for the hertz fit
    params.add('Awhite', value=Awhite_0, min=Awhite_lb, max=Awhite_ub)
    params.add('A', value=A_0, min=A_lb, max=A_ub)
    params.add('fR', value=fR_0, min=fR_lb, max=fR_ub)
    params.add('Q', value=Q_0, min=Q_lb, max=Q_ub)

    func_sho = Model(SHO_model)

    print(f'SHO parameter names: {func_sho.param_names}')
    print(f'SHO independent variables: {func_sho.independent_vars}')

    return func_sho.fit(ampl, params, freq=freq)


if __name__ == "__main__":
    # filepath = "/Users/javierlopez/Documents/jpkautomation-analysis/exps/PFQNM-H2O-thermal-noise-data_vDeflection_2022.01.12-11.37.51.tnd"
    # thermal_data = loadThermal(filepath)
    test_k_calibration()