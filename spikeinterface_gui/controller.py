from .base import ControllerBase
from .myqt import QT
from spikeinterface.widgets.utils import get_unit_colors
from spikeinterface.toolkit import get_template_extremum_channel, get_template_channel_sparsity


import numpy as np

spike_dtype =[('sample_index', 'int64'), ('unit_index', 'int64'), 
    ('channel_index', 'int64'), ('segment_index', 'int64'),
    ('visible', 'bool'), ('selected', 'bool')]


# TODO rename later
# cluster_visible > unit_visible
# cluster_visibility_changed > unit_visibility_changed

class  SpikeinterfaceController(ControllerBase):
    
    
    def __init__(self, waveform_extractor=None,parent=None):
        ControllerBase.__init__(self, parent=parent)
        
        self.we = waveform_extractor
        
        # some direct attribute
        self.num_segments = self.we.recording.get_num_segments()
        self.sampling_frequency = self.we.recording.get_sampling_frequency()
        
        
        self.colors = get_unit_colors(self.we.sorting, map_name='Dark2', format='RGBA')
        self.qcolors = {}
        for unit_id, color in self.colors.items():
            r, g, b, a = color
            self.qcolors[unit_id] = QT.QColor(r*255, g*255, b*255)
        
        self.cluster_visible = {unit_id:True for unit_id in self.unit_ids}
        
        all_spikes = self.we.sorting.get_all_spike_trains(outputs='unit_index')
        
        num_spikes = np.sum(e[0].size for e in all_spikes)
        
        # make internal spike vector
        self.spikes = np.zeros(num_spikes, dtype=spike_dtype)
        pos = 0
        for i in range(self.num_segments):
            sample_index, unit_index = all_spikes[i]
            sl = slice(pos, pos+len(sample_index))
            self.spikes[sl]['sample_index'] = sample_index
            self.spikes[sl]['unit_index'] = unit_index
            #~ self.spikes[sl]['channel_index'] = 
            self.spikes[sl]['segment_index'] = i
            self.spikes[sl]['visible'] = True
            self.spikes[sl]['selected'] = False
        
        # extremum channel
        self.templates_median = self.we.get_all_templates(unit_ids=None, mode='median')
        self.templates_average = self.we.get_all_templates(unit_ids=None, mode='average')
        self.templates_std = self.we.get_all_templates(unit_ids=None, mode='std')
        
        
        sparsity_dict = get_template_channel_sparsity(waveform_extractor, method='best_channels',
                                peak_sign='neg', num_channels=10, radius_um=None, outputs='index')
        self.sparsity_mask = np.zeros((self.unit_ids.size, self.channel_ids.size), dtype='bool')
        for unit_index, unit_id in enumerate(self.unit_ids):
            chan_inds = sparsity_dict[unit_id]
            self.sparsity_mask[unit_index, chan_inds] = True
        
        self._extremum_channel = get_template_extremum_channel(self.we, peak_sign='neg', outputs='index')

    @property
    def channel_ids(self):
        return self.we.recording.channel_ids

    @property
    def unit_ids(self):
        return self.we.sorting.unit_ids
    
    
    def get_extremum_channel(self, unit_id):
        chan_ind = self._extremum_channel[unit_id]
        return chan_ind

    def on_cluster_visibility_changed(self):
        #~ print('on_cluster_visibility_changed')
        self.update_visible_spikes()
        ControllerBase.on_cluster_visibility_changed(self)

    def update_visible_spikes(self):
        for unit_index, unit_id in enumerate(self.unit_ids):
            mask = self.spikes['unit_index'] == unit_index
            self.spikes['visible'][mask] = self.cluster_visible[unit_id]
    
    def get_num_samples(self, segment_index):
        return self.we.recording.get_num_samples(segment_index=segment_index)
    
    
    def get_traces(self, trace_source='preprocessed', **kargs):
        # assert trace_source in ['preprocessed', 'raw']
        assert trace_source in ['preprocessed']
        
        if trace_source == 'preprocessed':
            rec = self.we.recording
        elif trace_source == 'raw':
            # TODO get with parent recording the non process recording
            pass
        
        traces = rec.get_traces(**kargs)
        return traces

    def get_contact_location(self):
        location = self.we.recording.get_channel_locations()
        return location
    
    def get_waveform_sweep(self):
        return self.we.nbefore, self.we.nafter
        
    def get_waveforms_range(self):
        return np.min(self.templates_average), np.max(self.templates_average)
    
    def get_waveforms(self, unit_id):
        return self.we.get_waveforms(unit_id)
    
    def get_common_sparse_channels(self, unit_ids):
        unit_indexes = [list(self.unit_ids).index(u) for u in unit_ids]
        chan_inds, = np.nonzero(self.sparsity_mask[unit_indexes, :].sum(axis=0))
        return chan_inds
        
