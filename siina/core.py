#  pylint: disable=too-many-instance-attributes, attribute-defined-outside-init
"""Main functionality (Radar -class)."""
import os

from numpy import asarray, mean, polyfit, vstack, hstack, linspace

from .dzt import read_dzt
from .filters import butterworth


class Radar:
    """Radar class to handle GPR measurement data."""

    def __init__(self, fileformat=None, filepath=None, dtype=None):
        """Initialize Radar class.

        Parameters
        ----------
        fileformat : str, optional
            Define fileformat.
            Currently supported fileformats are
                - dzt
            If not defined, tries to infer format from the datafile.
        filepath : str, optional
            GPR datafile.
        dtype : int or str
            Used dtype for the measurement.

        """
        self._main_channel = 0
        self._read_file = None
        if fileformat is not None and fileformat.lower() in {"gssi", "dzt"}:
            self.fileformat = "dzt"
            self._read_file = read_dzt

        if filepath is not None:
            self.read_file(filepath, dtype=dtype)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        msg = "siina Radar class\n"
        if hasattr(self, "data_list"):
            msg += "  channels: {}".format(len(self.data_list))
            for i, _data in enumerate(self.data_list):
                msg += "\n    channel {}: samples {}, profile steps {}".format(i + 1, *_data.shape)
        return msg

    def set_fileformat(self, fileformat):
        """Set specific fileformat.

        Parameters
        ----------
        fileformat : str, optional
            Define fileformat.
            Currently supported fileformats are
                - dzt (gssi)

        Raises
        ------
        ValueError
            If fileformat has wrong or unsupported type.

        """
        if fileformat.lower() in {"gssi", "dzt"}:
            self._read_file = read_dzt
            self.fileformat = "dzt"
        else:
            err_msg = "Unknown fileformat: {}\nknown formats are:\n\t'dzt' or 'gssi'"
            raise ValueError(err_msg.format(fileformat))

    def read_file(self, filepath, dtype=None):
        """Read and process GPR datafile.

        Parameters
        ----------
        filepath : str
            GPR datafile.
        dtype : int or str
            Used dtype for the measurement.

        """
        if self._read_file is None:
            if isinstance(filepath, str):
                _, ext = os.path.splitext(filepath)
            elif hasattr(filepath, "name"):
                _, ext = os.path.splitext(filepath.name)
            else:
                raise ValueError("Missing the fileformat, could not deduce from the filename")
            # strip dot(s)
            self.set_fileformat(ext.strip("."))

        header, data = self._read_file(filepath, dtype=dtype)
        self.header = header

        self.data_list = []
        self._original_dtypes = []
        for _data in data:
            dtype = str(_data.dtype)
            self._original_dtypes.append(dtype)
            if "int" in dtype and dtype.startswith("u"):
                dtype = dtype.lstrip("u")
            self.data_list.append(_data.astype(dtype))

        self.nrows, self.ncols = None, None
        for _data in self.data_list:
            if hasattr(_data, "shape") and len(_data.shape) == 2:
                self.nrows, self.ncols = _data.shape
                break
        self.nchan = len(data)

    @property
    def data(self):  # pylint: disable=inconsistent-return-statements
        """Access function for data."""
        if hasattr(self, "data_list"):
            return self.data_list[self._main_channel]

    def read_markers(self, **kwargs):
        """Read and process markers.

        Parameters
        ----------
        kwargs
            Dictionary is re-directed to 'read marker function'

        """
        if self.fileformat == "dzt":
            self._read_dzt_markers(**kwargs)

    def _read_dzt_markers(self, interpolate=True):
        """Read dzt markers.

        Parameters
        ----------
        interpolate : bool
            If True, interpolate the first n missing points with second
            order polynomial.

        """
        self._markers0 = self.data[0, :].copy() - self.data[0, 0]
        self._markers1 = self.data[1, :].copy()
        self._marker_idx, *_ = self._markers1.nonzero()
        dtype = str(self._markers1.dtype)
        if "int" not in dtype:
            dtype = "uint64"
        if not dtype.startswith("u"):
            dtype = "u" + dtype
        self._marker_val = self._markers1[self._marker_idx].astype(dtype)
        self._marker_val2 = asarray(
            [int(format(item, "b")[::-1], base=2) for item in self._marker_val]
        )
        self._marker_hex = asarray([hex(item) for item in self._marker_val])
        self.markers = vstack((self._marker_idx, self._marker_val2))

        if interpolate:
            mean_signal = self.data[2:5, :].mean(1)
            theta2, theta1, theta0 = polyfit([0, 1, 2], mean_signal, 2)
            interpolated_0 = theta2 * -2 + theta1 * -2 + theta0
            interpolated_1 = theta2 * -1 + theta1 * -1 + theta0
            self.data[0, :] = interpolated_0
            self.data[1, :] = interpolated_1

    def convert_to_float64(self, channel=None):
        """Normalize data dtype to float64.

        Parameters
        ----------
        channel : int
            select specific channel if needed.
        """
        if hasattr(self, "data_list"):
            if channel is None:
                for i, _data in enumerate(self.data_list):
                    self.data_list[i] = _data.astype("float64")
            else:
                _data = self.data_list[channel]
                self.data_list[channel] = _data.astype("float64")

    def prop_sample_time(self, zero=0):
        """Get sample time array.

        Parameters
        ----------
        zero : int or float
            Non-center the output.

        Returns
        -------
        ndarray
            ndarray from '0 - zero' to 'sample_range - zero'

        """
        sample_range = self.header.get("range")
        n = self.nrows
        return linspace(0, sample_range, n) - zero

    def prop_profile_time(self, timeshift=0):
        """Get profile time array.

        Parameters
        ----------
        timeshift : int or float
            Non-center the output.

        Returns
        -------
        ndarray
            ndarray from '0 - timeshift' to 'sample_range - timeshift'

        """
        sps = self.header.get("samples_per_second")
        n = self.ncols
        return linspace(0, sps * n, n) - timeshift

    def prop_profile_distance(self, shift=0, reverse=False):
        """Get profile distance array.

        Parameters
        ----------
        shift : int or float
            Non-center the output.
        reverse : bool
            Flip order.

        Returns
        -------
        ndarray
            ndarray from '0 - shift' to 'sample_range - shift'

        """
        spm = self.header.get("samples_per_meter")
        n = self.ncols
        if reverse:
            distance = linspace(0, spm * n, n)[::-1] - shift
        else:
            distance = linspace(0, spm * n, n) - shift
        return distance

    def prop_coordinates(self):
        """Not implemented."""
        raise NotImplementedError

    # pylint: disable=inconsistent-return-statements
    def func_filter(self, cutoff, channel=0, btype="low", inplace=True, **kwargs):
        """Filter wrapper function.

        Parameters
        ----------
        cutoff : str or float
            filter parameter
        channel : int
            default channel
        btype : str
            filter type (low or high)

        Returns
        -------
        ndarray
            Filtered ndarray.

        """
        frequency = self.header["frequency"] / 1e9

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
        sps = self.header["samples_per_scan"]
        sample_range = self.header["range"]
        fs = frequency * sps / sample_range

        if inplace:
            # data, cutoff, fs, order=6, btype='lowpass', axis=0
            dtype = self.data_list[channel].dtype
            self.data_list[channel][:] = butterworth(
                data=self.data_list[channel], cutoff=cutoff, fs=fs, btype=btype, **kwargs
            ).astype(dtype)
        else:
            filtered_arr = butterworth(
                data=self.data_list[channel], cutoff=cutoff, fs=fs, btype=btype, **kwargs
            )
            return filtered_arr

    # pylint: disable=inconsistent-return-statements
    def func_dc(self, channel=0, shift=None, inplace=True, **kwargs):
        """Re-center data (DC-shift).

        Parameters
        ----------
        channel : int
        shift : int or float
        inplace : bool

        """
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
            if hasattr(shift, "__iter__"):
                shift = shift.astype(dtype)
            else:
                shift = hstack(shift).astype(dtype)[0]
            self.data_list[channel] -= shift
        else:
            return self.data_list[channel] - shift

    def to_dzt(self, path, **kwargs):
        """Not implemented."""
        raise NotImplementedError

    def to_rd3(self, path, **kwargs):
        """Not implemented."""
        raise NotImplementedError
