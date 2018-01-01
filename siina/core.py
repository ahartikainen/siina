from .dzt import read_dzt
from .filters import butterworth
import os
from numpy import asarray, mean, polyfit, vstack, hstack

class RadarFile:

    def __init__(self, fileformat=None):
        self._main_channel = 0
        if fileformat is not None and fileformat.lower() in {'gssi', 'dzt'}:
            self.fileformat = 'dzt'
            self._read_file = read_dzt
        else:
            self._read_file = None

    def set_fileformat(self, fileformat):
        if fileformat.lower() in {'gssi', 'dzt'}:
            self._read_file = read_dzt
            self.fileformat = 'dzt'
        else:
            err_msg = "Unknown fileformat: {}\nknown formats are:\n\t'dzt' or 'gssi'"
            raise ValueError(err_msg.format(fileformat))

    def read_file(self, filepath):
        if self._read_file is None:
            if isinstance(filepath, str):
                _, ext = os.path.splitext(filepath)
            elif hasattr(filepath, 'name'):
                _, ext = os.path.splitext(filepath.name)
            else:
                raise ValueError("Missing the fileformat, could not deduce from the filename")
            # strip dot(s)
            self.set_fileformat(ext.strip("."))

        header, data = self._read_file(filepath)
        self.header = header
        
        self.data_list = data
        
        self.nrows, self.ncols = None, None
        for _data in data_list:
            if len(_data):
                self.nrows, self.ncols = _data.shape
                break
        self.nchan = len(data)
        

    @property
    def data(self):
        if hasattr(self, 'data_list'):
            return self.data_list[self._main_channel]
        else:
            return None
    
    def read_markers(self, **kwargs):
        """

        """
        if self.fileformat == 'dzt':
            self._read_dzt_markers(**kwargs)
        else:
            pass

    def _read_dzt_markers(self, interpolate=True, **kwargs):
        self._markers0 = self.data[0, :].copy()-self.data[0,0]
        self._markers1 = self.data[1, :].copy()
        self._marker_idx, *_ = self._markers1.nonzero()
        dtype = str(self._markers1.dtype)
        if 'int' not in dtype:
            dtype = 'uint64'
        if not dtype.startswith('u'):
            dtype = 'u' + dtype
        self._marker_val = self._markers1[self._marker_idx].astype(dtype)
        self._marker_val2 = asarray([int(format(item, "b")[::-1], base=2) for item in self._marker_val])
        self._marker_hex = asarray([hex(item) for item in self._marker_val])
        self.markers = vstack((self._marker_idx, self._marker_val2))

        if interpolate:
            mean_signal = self.data[2:5, :].mean(1)
            m2, m, b = polyfit([0,1,2], mean_signal, 2)
            interpolated_0 = m2 * -2 + m * -2 + b
            interpolated_1 = m2 * -1 + m * -1 + b
            self.data[0, :] = interpolated_0
            self.data[1, :] = interpolated_1

    def prop_sample_time(self, zero=0):
        sample_range = self.header.get("range")
        n = self.nrows
        return np.linspace(0, sample_range, n) - zero

    def prop_profile_time(self, timeshift=0):
        sps = self.header.get("samples_per_second")
        n = self.ncols
        return np.linspace(0, sps * n, n) - timeshift

    def prop_profile_distance(self, shift=0, reverse=False):
        spm = self.header.get("samples_per_meter")
        n = self.ncols
        if reverse:
            distance = np.linspace(0, spm * n, n)[::-1] - shift
        else:
            distance = np.linspace(0, spm * n, n) - shift
        return distance

    def prop_coordinates(self):
        pass

    def func_filter(self, cutoff, channel=0, btype='low', inplace=True, **kwargs):

        frequency = self.header['frequency'] / 1e9

        if isinstance(cutoff, str):
            cutoff = frequency * float(cutoff)
        elif isinstance(cutoff, (list, tuple)) and len(cutoff) == 2:
            cutoff = list(cutoff)
            if isinstance(cutoff[0], str):
                cutoff[0] = frequency * float(cutoff[0])
            if isinstance(cutoff[1], str):
                cutoff[1] = frequency * float(cutoff[1])
            cutoff = tuple(cutoff)
        # sampling frequency
        sps = self.header['samples_per_scan']
        sample_range = self.header['range']
        fs = frequency * sps / sample_range

        if inplace:
            # data, cutoff, fs, order=6, btype='lowpass', axis=0
            dtype = self.data_list[channel].dtype
            self.data_list[channel][:] = butterworth(data = self.data_list[channel],
                                                     cutoff = cutoff,
                                                     fs = fs,
                                                     btype=btype,
                                                     **kwargs).astype(dtype)
            return None
        else:
            filtered_arr = butterworth(data = self.data_list[channel],
                                       cutoff = cutoff,
                                       fs = fs,
                                       btype=btype,
                                       **kwargs)
            return filtered_arr

    def func_dc(self, channel=0, shift=None, inplace=True, **kwargs):

        start = kwargs.pop("start", None)
        end = kwargs.pop("end", None)
        step = kwargs.pop("step", None)

        method = kwargs.pop("method", mean)
        axis = kwargs.pop("axis", 0)

        if shift is None:
            shift = method(self.data_list[channel][start:end:step], axis=axis)
            if axis == 1:
                shift = shift[:, None]

        if inplace:
            dtype = self.data_list[channel].dtype
            if hasattr(shift, '__iter__'):
                shift = shift.astype(dtype)
            else:
                shift = hstack(shift).astype(dtype)[0]
            self.data_list[channel] -= shift
        else:
            return self.data_list[channel] - shift

    def to_dzt(self, path, **kwargs):
        pass

    def to_rd3(self, path, **kwargs):
        pass
