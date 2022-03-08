from pyafmrheo.utils.force_curves import *

def preprocess_curve(file_data, curve_idx, height_channel, deflection_sensitivity):

    force_curve = file_data[curve_idx]

    extend_segments = force_curve.extend_segments
    pause_segments = force_curve.pause_segments
    modulation_segments = force_curve.modulation_segments
    retract_segments = force_curve.retract_segments

    force_curve_segments = [*extend_segments, *pause_segments, *modulation_segments, *retract_segments]
    processed_segments = []

    for seg_id, segment in force_curve_segments:
        segment_type = segment.segment_type
        seg_deflection, seg_height, seg_time =\
            preprocess_segment(segment, height_channel, deflection_sensitivity)
        if segment_type == 'modulation':
            frequency = segment.segment_metadata["frequency"]
            processed_segments.append((seg_id, segment_type, {'height': seg_height, 'deflection':seg_deflection, 'time':seg_time, 'frequency':frequency}))
        else:
            processed_segments.append((seg_id, segment_type, {'height': seg_height, 'deflection':seg_deflection, 'time':seg_time}))
    
    processed_segments = sorted(processed_segments, key=lambda x: int(x[0]))

    xzero = processed_segments[-1][2]['height'][-1]

    for seg_id, segment_type, data in processed_segments:
        data['height'] = xzero - data['height']
    
    return processed_segments

def FindValueIndex(seq, val):
    r = np.where(np.diff(np.sign(seq - val)) != 0)
    idx = r + (val - seq[r]) / (seq[r + np.ones_like(r)] - seq[r])
    idx = np.append(idx, np.where(seq == val))
    idx = np.sort(idx)
    return int(idx[0])

def get_retract_ramp_sizes(file_data, curve_idx):
    x0 = 0
    distances = []
    force_curve = file_data[curve_idx]
    sorted_ret_segments = sorted(force_curve.retract_segments, key=lambda x: int(x[0]))
    for _, first_ret_seg in sorted_ret_segments[:-1]:
        distance_from_sample = -1 * first_ret_seg.segment_metadata['ramp_size'] + x0 # Negative
        distances.append(distance_from_sample * 1e-9)
        x0 = distance_from_sample
    return distances