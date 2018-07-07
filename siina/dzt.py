from datetime import datetime
import struct
from numpy import dtype as numpy_dtype, fromfile

DZT_HEADER_STRUCT = "=4Hh5fH4s4s7H3f31sc14sH12sH896s"
DZT_HEADER_BYTES = 1024


def dzt_header_date(date_bytes):
    """Transform 4 (dense) bytes to datetime following the DZT-date format

    Parameters
    ----------
    date_bytes : bytes
        4 byte long bytes object.

    Returns
    -------
    date : datetime
        Date in datetime format.
    date tuple: tuple
        In a case if datetime object is not well defined.
        Tuple format = (year + 1980, month, day, hour, minutes, seconds=sec*2)
    """
    # Little endian binary --> number to binary array with [::-1]
    binary_array = format(struct.unpack("<I", date_bytes)[0], "b").zfill(32)[::-1]

    # Transform array back to number with [::-1]
    # Values are uint --> python int with binary repr will work
    sec2 = int(binary_array[0:5][::-1], base=2)  # 5-bits 00-04  0-29 (second/2)
    minutes = int(binary_array[5:11][::-1], base=2)  # 6-bits 05-10  0-59
    hour = int(binary_array[11:16][::-1], base=2)  # 5-bits 11-15  0-23
    day = int(binary_array[16:21][::-1], base=2)  # 5-bits 16-20  1-31
    month = int(
        binary_array[21:25][::-1], base=2
    )  # 4-bits 21-24  1-12, 1=Jan, 2=Feb, etc.
    year = int(
        binary_array[25:32][::-1], base=2
    )  # 7-bits 25-31  0-127 (0-127 = 1980-2107)

    value_range_pairs = (
        (sec2, (0, 30)),
        (minutes, (0, 60)),
        (hour, (0, 24)),
        (day, (1, 32)),
        (month, (1, 13)),
        (year, (0, 128)),
    )

    if all((v >= lb) & (v < ub) for v, (lb, ub) in value_range_pairs):
        return datetime(1980 + year, month, day, hour, minutes, sec2 * 2)
    else:
        return (1980 + year, month, day, hour, minutes, sec2 * 2)


def read_dzt(filepath, fileformat=None, dtype=None, **kwargs):
    """
    Parameters
    ----------
    filepath : str or fileobject
        Path to dzt-file or -fileobject with `.read` method returning bytes.
    fileformat : int, optional
        Format for the DZT structure.
        Default is to infer the format from the header
        fileformat=0, old format with 1024 header,
            Data starts after `1024 * nchan` bytes.
        fileformat=1, new format with 1024 header,
            Data starts after `1024 * data` bytes.
    dtype : int or str, optional
        Number format for the data.
    samples_per_scan : int, optional
    channels : int, optional
    read_header_function : function
        Function to read header.
        Parameters
        - f
        - fileformat
        - **kwargs
        Returns
        dictionary with optional keys:
        - bits
        - samples_per_scan
        - channels
        - skip_initial

    Returns
    -------
    header : dictionary
        First header, length of 1024 bytes, unpacked.
        Other headers are found as a list of bytes under `'other_headers'`.
    data : list of numpy arrays
        Each channel in Fortran (column oriented) format.
        In case of failing to reshape, returns one numpy array in a list.
        Error message is found in the header-dict.
    """

    def read(f, **kwargs):
        # parse kwargs
        _read_dzt_header = kwargs.pop("read_header_function", read_dzt_header)
        dtype = kwargs.pop("dtype", None)
        samples_per_scan = kwargs.pop("samples_per_scan", None)
        channels = kwargs.pop("channels", None)
        skip_initial = kwargs.pop("skip_initial", None)

        # read header
        header = _read_dzt_header(f, fileformat, **kwargs)

        if dtype is None:
            dtype = header.get("bits", None)
        if samples_per_scan is None:
            samples_per_scan = header.get("samples_per_scan", None)
        if channels is None:
            channels = header.get("channels", None)
        if skip_initial is None:
            skip_initial = header.get("skip_initial", None)

        # read data
        data, errmsg = read_dzt_data(
            f,
            dtype=dtype,
            samples_per_scan=samples_per_scan,
            channels=channels,
            skip_initial=skip_initial,
            **kwargs,
        )

        return header, data, errmsg

    if isinstance(filepath, str):
        with open(filepath, "rb") as f:
            header, data, errmsg = read(f, **kwargs)
    else:
        header, data, errmsg = read(filepath, **kwargs)

    # Add error message to header
    header["errmsg"] = errmsg

    return header, data


def read_dzt_header(fileobject, fileformat=None, **kwargs):
    """
    Parameters
    ----------
    fileobject : fileobject
        Object with `.read` method returning bytes.
    fileformat : int, optional
        Format for the DZT structure.
        Default is to infer the format from the header.
        fileformat=0, old format with 1024 header,
            Data starts after `1024 * nchan` bytes.
        fileformat=1, new format with 1024 header,
            Data starts after `1024 * data` bytes.
    encoding : str, optional
        Encoding used for the decoding bytes to string.
        Default is 'ascii'.
    frequency : float or a list of floats, optional
        Central antenna frequency for each channel.

    Returns
    -------
    header : dictionary
        First header, lenght of 1024, unpacked.
        Other headers are found as a list of bytes under `'other_headers'`.
    """
    encoding = kwargs.get("encoding", "ascii")
    frequency = kwargs.get("frequency", None)

    # read the first header
    header = fileobject.read(DZT_HEADER_BYTES)

    # unpack header information
    (
        tag,
        data,
        nsamp,
        bits,
        zero,
        sps,
        spm,
        mpm,
        position,
        range,
        npass,
        create,
        modif,
        rgain,
        nrgain,
        text,
        ntext,
        proc,
        nproc,
        nchan,
        epsr,
        top,
        depth,
        reserved,
        dtype,
        antname,
        chanmask,
        name,
        chksum,
        variable,
    ) = struct.unpack(DZT_HEADER_STRUCT, header)

    tag_bytes = struct.pack("H", tag)
    tag_bits = format(tag, "b")
    create_datetime = dzt_header_date(create)
    modif_datetime = dzt_header_date(modif)
    reserved_decoded = (
        reserved.decode(encoding, "ignore")
        .replace("\x00", " ")
        .replace("  ", " ")
        .strip()
    )
    dtype_char = struct.pack("c", dtype)
    antname_decoded = (
        antname.decode(encoding, "ignore")
        .replace("\x00", " ")
        .replace("  ", " ")
        .strip()
    )
    name_decoded = (
        name.decode(encoding, "ignore").replace("\x00", " ").replace("  ", " ").strip()
    )
    variable_decoded = (
        variable.decode(encoding, "ignore")
        .replace("\x00", " ")
        .replace("  ", " ")
        .strip()
    )

    channels = nchan
    samples_per_scan = nsamp
    samples_per_second = sps
    samples_per_meter = spm
    meters_per_mark = mpm

    if frequency is None:
        if antname_decoded.startswith("41"):
            frequency = 1e9
        elif antname_decoded.startswith("42"):
            frequency = 2e9

    # Check the fileformat based on the `data` property
    if fileformat is None:
        if data != 1024:
            fileformat = 1
        else:
            fileformat = 0

    # Read extra headers based on the first header information
    if fileformat:
        # Information of the header length is in the `data` property
        extra_bytes = DZT_HEADER_BYTES * (data - 1)
    else:
        # Each channel has their own header
        extra_bytes = DZT_HEADER_BYTES * (nchan - 1)

    # Read in the rest of the header
    other_headers = []
    other_headers_decoded = {}
    extra_round = 0
    extra_header = fileobject.read(extra_bytes)
    while extra_header:
        # Insert extra header to a list with chunks of `header_bytes` bytes
        other_header = extra_header[:DZT_HEADER_BYTES]
        other_headers.append(other_header)

        other_header_decoded = (
            other_header.decode(encoding, "ignore")
            .replace("\x00", "")
            .replace("  ", " ")
            .strip()
        )
        if len(other_header_decoded):
            other_headers_decoded[extra_round] = other_header_decoded

        extra_header = extra_header[DZT_HEADER_BYTES:]
        extra_round += 1

    header_dict = {
        "tag": tag,
        "tag_bytes": tag_bytes,
        "tag_bits": tag_bits,
        "data": data,
        "nsamp": nsamp,
        "samples_per_scan": samples_per_scan,
        "bits": bits,
        "zero": zero,
        "sps": sps,
        "samples_per_second": samples_per_second,
        "spm": spm,
        "samples_per_meter": samples_per_meter,
        "mpm": mpm,
        "meters_per_mark": meters_per_mark,
        "position": position,
        "range": range,
        "npass": npass,
        "create": create,
        "create_datetime": create_datetime,
        "modif": modif,
        "modif_datetime": modif_datetime,
        "rgain": rgain,
        "nrgain": nrgain,
        "text": text,
        "ntext": ntext,
        "proc": proc,
        "nproc": nproc,
        "nchan": nchan,
        "channels": channels,
        "epsr": epsr,
        "top": top,
        "depth": depth,
        "reserved": reserved,
        "reserved_decoded": reserved_decoded,
        "dtype": dtype,
        "dtype_char": dtype_char,
        "antname": antname,
        "antname_decoded": antname_decoded,
        "chanmask": chanmask,
        "name": name,
        "name_decoded": name_decoded,
        "chksum": chksum,
        "variable": variable,
        "variable_decoded": variable_decoded,
        "frequency": frequency,
        "fileformat": fileformat,
        "extra_bytes": extra_bytes,
        "DZT_HEADER_STRUCT": DZT_HEADER_STRUCT,
        "DZT_HEADER_BYTES": DZT_HEADER_BYTES,
        "other_headers": other_headers,
        "other_headers_decoded": other_headers_decoded,
    }
    return header_dict


def read_dzt_data(fileobject, dtype, samples_per_scan=None, channels=None, **kwargs):
    """
    Parameters
    ----------
    fileobject : fileobject
        Object with `.read` method returning bytes.
    dtype : int or str, optional
        Number format for the data.
        For ints assume:
             8 = 'uint8'
            16 : 'uint16'
            32 : 'int32'
            64 : 'int64'
    samples_per_scan : int, optional
    channels : int, optional
    skip_initial : int, optional
        Skip first `skip_initial` bytes.
        Default is 0 bytes.

    Returns
    -------
    data : list of ndarrays
        Each channel in Fortran format (column oriented).
        In case of failing to reshape, returns one numpy array in a list
    error_message : str
    """
    skip_initial = kwargs.get("skip_initial", None)

    dtype_dict = {8: "uint8", 16: "uint16", 32: "int32", 64: "int64"}

    if not isinstance(dtype, str):
        dtype = dtype_dict[dtype]

    dtype = numpy_dtype(dtype)

    if skip_initial is not None:
        fileobject.read(skip_initial)

    # count = -1 :: read to end of the file
    data_array = fromfile(fileobject, count=-1, dtype=dtype)

    if (samples_per_scan is None) or (data_array.size % samples_per_scan != 0):
        if samples_per_scan is None:
            samples_per_scan = "None"

        err_msg = "error in samples_per_scan : divmod({}, {}) = div:{}, mod:{}"
        dsize = data_array.size
        sps = samples_per_scan
        div, mod = divmod(data_array.size, samples_per_scan)
        return [data_array], err_msg.format(dsize, sps, div, mod)

    N = samples_per_scan
    D = data_array.size // samples_per_scan
    data_array = data_array.reshape(N, D, order="F")

    if not channels:
        err_msg = "channel count is: {}"
        return [data_array], err_msg.format(channels)

    data = []
    for channel in range(channels):
        # Slice array with start:end:step
        #     start = (0, 1, ...),
        #     end = None
        #     step=number of channels
        data.append(data_array[:, channel::channels])

    return data, None
