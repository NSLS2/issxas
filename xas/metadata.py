from collections import OrderedDict
from datetime import datetime


metadata_dict = OrderedDict({
'Facility':                     {'kind' : 'auto',                                                                   'human_readable_key': 'Facility.name'},
'nslsii_status':                {'kind' : 'attribute',                                                              'human_readable_key': 'Facility.mode'},
'nslsii_current':               {'kind' : 'epics_pv',                                                               'human_readable_key': 'Facility.current'},
'nslsii_energy':                {'kind' : 'attribute',                                                              'human_readable_key': 'Facility.current'},
'year':                         {'kind' : 'auto',                                                                   'human_readable_key': 'Facility.year'},
'cycle':                        {'kind' : 'auto',                                                                   'human_readable_key': 'Facility.cycle'},
'proposal':                     {'kind' : 'auto',                                                                   'human_readable_key': 'Facility.GUP'},
'saf':                          {'kind' : 'auto',                                                                   'human_readable_key': 'Facility.SAF'},
'PI':                           {'kind' : 'auto',                                                                   'human_readable_key': 'Experimenter.name'},
'beamline_id':                  {'kind' : 'auto',                                                                   'human_readable_key': 'Beamline.name'},
'beamline_source':              {'kind' : 'fixed_value', 'value' : 'damping wiggler',                               'human_readable_key': 'Beamline.x-ray_source'},
'beamline_cm1':                 {'kind' : 'attribute',                                                              'human_readable_key': 'Beamline.collimation_mirror1.material'},
'beamline_cm2':                 {'kind' : 'attribute',                                                              'human_readable_key': 'Beamline.collimation_mirror2.material'},
'beamline_cm2_bender':          {'kind' : 'epics_pv',                                                               'human_readable_key': 'Beamline.collimation_mirror2.bender_loading'},
'beamline_fm_geometry':         {'kind' : 'fixed_value', 'value' : 'toroidal mirror',                               'human_readable_key': 'Beamline.focusing'},
'beamline_fm':                  {'kind' : 'attribute',                                                              'human_readable_key': 'Beamline.focusing.material'},
'beamline_fm_bender':           {'kind' : 'epics_pv',                                                               'human_readable_key': 'Beamline.focusing.bender_loading'},
'beamline_harmonic_rejection':  {'kind' : 'attribute',                                                              'human_readable_key': 'Beamline.harmonic_rejection'},
'mono_name':                    {'kind' : 'fixed_value', 'value' : 'Si(111)',                                       'human_readable_key': 'Mono.scan_mode'},
'mono_d_spacing':               {'kind' : 'fixed_value', 'value' : '3.1354951',                                     'human_readable_key': 'Mono.d_spacing'},
'mono_scan_mode':               {'kind' : 'fixed_value', 'value' : 'pseudo-channel cut',                            'human_readable_key': 'Mono.scan_mode'},
'experiment':                   {'kind' : 'auto',                                                                   'human_readable_key': 'Mono.scan_type'},
'trajectory_filename':          {'kind' : 'auto',                                                                   'human_readable_key': 'Mono.trajectory_name'},
'mono_direction':               {'kind' : 'auto',                                                                   'human_readable_key': 'Mono.direction'},
'angle_offset':                 {'kind' : 'epics_pv',                                                               'human_readable_key': 'Mono.angle_offset'},
'angle_offset_deg':             {'kind' : 'attribute',                                                              'human_readable_key': 'Mono.angle_offset'},
'mono_encoder_resolution':      {'kind' : 'attribute',                                                              'human_readable_key': 'Mono.encoder_resolution'},
'detector_i0':                  {'kind' : 'fixed_value', 'value' : 'ion chamber',                                   'human_readable_key': 'Detector.I0'},
'detector_it':                  {'kind' : 'fixed_value', 'value' : 'ion chamber',                                   'human_readable_key': 'Detector.I1'},
'detector_ir':                  {'kind' : 'fixed_value', 'value' : 'ion chamber',                                   'human_readable_key': 'Detector.I2'},
'detector_if':                  {'kind' : 'fixed_value', 'value' : 'PIPS',                                          'human_readable_key': 'Detector.IF'},
'detector_i0_length':           {'kind' : 'fixed_value', 'value' : '15 cm',                                         'human_readable_key': 'Detector.I0.length'},
'detector_it_length':           {'kind' : 'fixed_value', 'value' : '15 cm',                                         'human_readable_key': 'Detector.I1.length'},
'detector_ir_length':           {'kind' : 'fixed_value', 'value' : '15 cm',                                         'human_readable_key': 'Detector.I2.length'},
'detector_if_thickness':        {'kind' : 'fixed_value', 'value' : '500 um',                                        'human_readable_key': 'Detector.IF.thickness'},
'detector_i0_n2':               {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I0.gas.N2'},
'detector_it_n2':               {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I1.gas.N2'},
'detector_ir_n2':               {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I2.gas.N2'},
'detector_i0_he':               {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I0.gas.He'},
'detector_it_he':               {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I1.gas.He'},
'detector_ir_he':               {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I2.gas.He'},
'detector_i0_volt':             {'kind' : 'epics_pv',                                                               'human_readable_key': 'Detector.I0.voltage'},
'detector_it_volt':             {'kind' : 'epics_pv',                                                               'human_readable_key': 'Detector.I1.voltage'},
'detector_ir_volt':             {'kind' : 'epics_pv',                                                               'human_readable_key': 'Detector.I2.voltage'},
'i0_gain':                      {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I0.gain'},
'it_gain':                      {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I1.gain'},
'ir_gain':                      {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.I2.gain'},
'iff_gain':                     {'kind' : 'attribute',                                                              'human_readable_key': 'Detector.IF.gain'},
'detectors':                    {'kind' : 'auto',                                                                   'human_readable_key': 'Detector.aux'},
'element':                      {'kind' : 'auto',                                                                   'human_readable_key': 'Element.symbol'},
'edge':                         {'kind' : 'auto',                                                                   'human_readable_key': 'Element.edge'},
'line':                         {'kind' : 'auto',                                                                   'human_readable_key': 'Element.line'},
'scan_id':                      {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.transient_id'},
'uid':                          {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.uid'},
'e0':                           {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.edge_energy.eV'},
'time':                         {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.start_time'},
'stop_time':                    {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.end_time'},
'name':                         {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.name'},
'comment':                      {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.comment'},
'attenuation':                  {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.attenuation'},
'reference_foil':               {'kind' : 'auto',                                                                   'human_readable_key': 'Scan.reference_foil'},
'sample_name':                  {'kind' : 'auto',                                                                   'human_readable_key': 'Sample.name'},
'sample_comment':               {'kind' : 'auto',                                                                   'human_readable_key': 'Sample.comment'},
'sample_x_position':            {'kind' : 'epics_pv',                                                               'human_readable_key': 'Sample.position.x.mm'},
'sample_y_position':            {'kind' : 'epics_pv',                                                               'human_readable_key': 'Sample.position.y.mm'},
'sample_z_position':            {'kind' : 'epics_pv',                                                               'human_readable_key': 'Sample.position.z.mm'},
'sample_th_position':           {'kind' : 'epics_pv',                                                               'human_readable_key': 'Sample.position.theta.deg'},
'sample_heater_1_T_sp' :        {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-HTR:1}T-SP',                     'human_readable_key': 'SampleHeater.temperature1.setpoint.celsius'},
'sample_heater_1_T_rb':         {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B2:5}InCh0:Data-I',          'human_readable_key': 'SampleHeater.temperature1.readback.celsius'},
'sample_heater_1_curr_sp':      {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B2:3}OutCh0:Data-SP',        'human_readable_key': 'SampleHeater.current.setpoint'},
'sample_heater_1_curr_rb' :     {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B2:3}OutCh0:Data-RB',        'human_readable_key': 'SampleHeater.current.readback'},
'sample_heater_2_T_sp' :        {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-HTR:2}T-SP',                     'human_readable_key': 'SampleHeater.temperature2.setpoint.celsius'},
'sample_heater_2_T_rb':         {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B2:5}InCh1:Data-I',          'human_readable_key': 'SampleHeater.temperature2.readback.celsius'},
'sample_heater_2_volt_sp':      {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B1:11}OutCh0:Data-SP',       'human_readable_key': 'SampleHeater.voltage.setpoint'},
'sample_heater_2_volt_rb' :     {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B1:11}OutCh0:Data-RB',       'human_readable_key': 'SampleHeater.voltage.readback'},
'sample_cryostat_a_T_rb' :      {'kind' : 'epics_pv', 'pv_str': 'XF:08ID-ES{LS:331-1}:SAMPLE_A',                    'human_readable_key': 'SampleCryostat.temperature.A.readback.kelvin'},
'sample_cryostat_b_T_rb' :      {'kind' : 'epics_pv', 'pv_str': 'XF:08ID-ES{LS:331-1}:SAMPLE_B',                    'human_readable_key': 'SampleCryostat.temperature.B.readback.kelvin'},
'sample_heater_PID_KP' :        {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{FbPid:01}PID.KP',                      'human_readable_key': 'SampleHeater.PID.P'},
'sample_heater_PID_KI' :        {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{FbPid:01}PID.KI',                      'human_readable_key': 'SampleHeater.PID.I'},
'sample_heater_PID_KD' :        {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{FbPid:01}PID.KD',                      'human_readable_key': 'SampleHeater.PID.D'},
'gc_mfc_ch4_sp'  :              {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:1}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.CH4.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_ch4_rb'  :              {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:1}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.CH4.readback.sccm', 'notation': "3.1f"},
'gc_mfc_co_sp':                 {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:2}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.CO.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_co_rb':                 {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:2}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.CO.readback.sccm', 'notation': "3.1f"},
'gc_mfc_h2_sp':                 {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:3}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.H2.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_h2_rb':                 {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:3}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.H2.readback.sccm', 'notation': "3.1f"},
'gc_mfc_exhaust_sp':            {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:4}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.exhaust.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_exhaust_rb':            {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:4}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.exhaust.readback.sccm', 'notation': "3.1f"},
'gc_mfc_aux5_sp':               {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:5}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.aux5.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_aux5_rb':               {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:5}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.aux5.readback.sccm', 'notation': "3.1f"},
'gc_mfc_inert_sp':              {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:6}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.inert.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_inert_rb':              {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:6}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.inert.readback.sccm', 'notation': "3.1f"},
'gc_mfc_aux7_sp':               {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:7}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.aux7.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_aux7_rb':               {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:7}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.aux7.readback.sccm', 'notation': "3.1f"},
'gc_mfc_aux8_sp':               {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:8}Gas:Flow-SP',               'human_readable_key': 'SampleGasCart.MFC.aux8.setpoint.sccm', 'notation': "3.1f"},
'gc_mfc_aux8_rb':               {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:8}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.aux8.readback.sccm', 'notation': "3.1f"},
# 'gc_mfc_exhaust_rb':            {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{GC:1-MFC:4}Gas:Flow-I',                'human_readable_key': 'SampleGasCart.MFC.exhaust.readback'},
'switch_valve_ghs':             {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B1:1}Out:0-Sel',             'human_readable_key': 'SampleSwitchValve.GHS.readback'},
'switch_valve_gas_cart':        {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B1:1}Out:1-Sel',             'human_readable_key': 'SampleSwitchValve.GasCart.readback'},
'switch_valve_intert':          {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-CT{DIODE-Box_B1:1}Out:2-Sel',             'human_readable_key': 'SampleSwitchValve.Inert.readback'},
'potentiostat_v':               {'kind' : 'epics_pv',                                                               'human_readable_key': 'Potentiostat.Voltage.readback'},
'potentiostat_i':               {'kind' : 'epics_pv',                                                               'human_readable_key': 'Potentiostat.Current.readback'},
})

_ghs_selected_gas_dict = OrderedDict()
for letter in ['a', 'b', 'c', 'd', 'e']:
    _ghs_selected_gas_dict[f'ghs_selected_gas_{letter}'] = {'kind' : 'epics_pv', 'pv_str': 'XF:08IDB-UT{Gas:1}Group:' + f'{letter.upper()}' + '-Sel', 'human_readable_key': f'SampleGasHandlingSystem.gas_{letter}.name'}

_ghs_mfc_dict = OrderedDict()
for i in range(1, 17):
    _ghs_mfc_dict[f'ghs_mfc_{i}_sp'] = {'kind': 'epics_pv', 'pv_str': 'XF:08IDB-UT{Gas:1-MFC:' + f'{i:02d}' + '}F:Target-SP','human_readable_key': f'SampleGasHandlingSystem.MFC{i}.setpoint.sccm', 'notation': "3.1f"}
    _ghs_mfc_dict[f'ghs_mfc_{i}_rb'] = {'kind': 'epics_pv', 'pv_str': 'XF:08IDB-UT{Gas:1-MFC:' + f'{i:02d}' + '}F-I',        'human_readable_key': f'SampleGasHandlingSystem.MFC{i}.readback.sccm', 'notation': "3.1f"}

_rga_dict = OrderedDict()
for i in range(1, 11):
    _rga_dict[f'rga_ch{i}_mass'] = {'kind': 'epics_pv', 'pv_str': 'XF:08IDB-VA{RGA:1}Mass:MID' + f'{i}',
                                        'human_readable_key': f'SampleGasHandlingSystem.RGA.ch{i}.mass.amu'}
    _rga_dict[f'rga_ch{i}_rb'] = {'kind': 'epics_pv',   'pv_str': 'XF:08IDB-SE{RGA:1}P:MID' + f'{i}' + '-I',
                                        'human_readable_key': f'SampleGasHandlingSystem.RGA.ch{i}.pressure.torr', 'notation': ".3E"}
    
# @TerribleHack to allow to work on RGA
# metadata_dict = {**metadata_dict, **_ghs_selected_gas_dict, **_ghs_mfc_dict, **_rga_dict}
metadata_dict = {**metadata_dict, **_ghs_selected_gas_dict, **_ghs_mfc_dict, **_rga_dict}

ghs_selected_gas_key_match = {
    'ghs_selected_gas_a': {0: 'None',   1: 'Phosphine',     2: 'Arsine'},
    'ghs_selected_gas_b': {0: 'None',   1: 'None',          2: 'Nitric Oxide'},
    'ghs_selected_gas_c': {0: 'None',   1: 'Methane',       2: 'Ethylene'},
    'ghs_selected_gas_d': {0: 'None',   1: 'None',          2: 'Hydrogen',      3: 'Ammonia'},
    'ghs_selected_gas_e': {0: 'None',   1: 'Ar',            2: 'CO2',           3: 'N2',        4: 'He'}}

key_match = {k : v['human_readable_key'] for k, v in metadata_dict.items()}


def generate_file_header_from_hdr(hdr):
    output = ''
    for key, hr_key in key_match.items():
        if key in hdr.start.keys():
            value = hdr.start[key]
        elif key == 'stop_time':
            value = hdr.stop['time']
        else:
            value = 'None'
        if (key == 'time') or (key == 'stop_time'):
            value = datetime.fromtimestamp(value).strftime('%m/%d/%Y  %H:%M:%S.%f')
        output += f'# {hr_key}: {value}\n'
    return output




def generate_xdi_metadata_from_hdr(hdr):
    output = {}
    for key, hr_key in key_match.items():
        if key in hdr.start.keys():
            value = hdr.start[key]
        elif key == 'stop_time':
            value = hdr.stop['time']
        else:
            value = 'None'
        if (key == 'time') or (key == 'stop_time'):
            value = datetime.fromtimestamp(value).strftime('%m/%d/%Y  %H:%M:%S.%f')
        output[str(hr_key)] = str(value)
    return output