

"""Experimental parser for total_chrom files from Perkin-Elmer GC's"""


from pprint import pprint
from struct import unpack, calcsize

from numpy import fromfile

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)


TYPE_TRANSLATION = {
    'Uint32': '>I',
    'int32': '>i',
    'long': '>l',
    'BOOL': '>xxx?',
}


#FILE_REFERENCE = (

#    FIXME
#)

FILE_HEADER = (
    ('signature', 'Uint32'),
    ('totalchrom_object_type', 'int32'),
    ('file_revision_number', 'Uint32'),
    ('technique', 'Uint32'),
    ('audit_log_flag', 'BOOL'),
    ('electronic_signature_enabled', 'BOOL'),
    ('audit_trail_offset', 'Uint32'),
    ('file_checksum', 'string'),
    ('header_checksum', 'string'),
)

DATA_HEADER = (
    ('author', 'string'),
    ('author_host', 'string'),
    ('time_and_date_created', 'pnw_date'),
    ('editor', 'string'),
    ('editor_host', 'string'),
    ('time_and_date_last_edited', 'pnw_date'),
    ('site_id', 'string'),
    ('number_of_times_edited_saved_since_creation', 'long'),
    ('edit_flags', 'int32'),
    ('file_description', 'string'),
)

RAW_DATA_HEADER = (
    ('data_header', DATA_HEADER),
    ('file_completion_flag', 'int32'),
    ('run_log', 'string'),
)

ADHEADER = (
    ('Instrument Number', 'int32'),
    ('Time and Date Started', 'pnw_date'),
    ('Channel Number', 'int32'),
    ('Operator Initials', 'string'),
    ('Sequence File Spec', 'string'), #FILE_REFERENCE),
    ('Sequence Entry #', 'int32'),
    ('Autosampler name', 'string'),
    ('Rack Number', 'int32'),
    ('Vial Number', 'int32'),
    ('Actual Run Time', 'double'),
    ('Raw Data Maximum', 'int32'),
    ('Raw Data Minimum', 'int32'),
    ('Interface serial number', 'string'),
    ('AIA raw data conversion scale factor', 'double'),
    ('AIA raw data conversion offset', 'double'),
    ('Number of Data Points', 'int32'),
    ('unknown_1', 'int32'),
    ('unkonwn_2', 'int32'),
)

SEQ_DESCRIPTION = (
    ('injection_site', 'string'),
    ('rack_number', 'int32'),
    ('vial_number', 'int32'),
    ('number_of_replicates', 'int32'),
    ('study_name', 'string'),
    ('sample_name', 'string'),
    ('sample_number', 'string'),
    ('raw_data_filename', 'string'),  # FILE REFERENCE
    ('result_data_filename', 'string'),  # FILE REFERENCE
    ('modified_raw_data_filename', 'string'),  # FILE REFERENCE
    ('baseline_data_filename', 'string'),  # FILE REFERENCE
    ('instrument_method', 'string'),  # FILE REFERENCE
    ('process_method', 'string'),  # FILE REFERENCE
    ('sample_method', 'string'),  # FILE REFERENCE
    ('report_format_file', 'string'),  # FILE REFERENCE
    ('printer_device', 'string'),
    ('plotter_device', 'string'),
    ('actual_sample_amount', 'double'),
    ('actual_istd_amount', 'double'),
    ('actual_sample_volume', 'double'),
    ('dilution_factor', 'double'),
    ('multiplier', 'double'),
    ('divisor', 'double'),
    ('addend', 'double'),
    ('normalization_factor', 'double'),
    ('calibration_report', 'int32'),
    ('calibration_level', 'string'),
    ('update_retention_times', 'int32'),
    ('sample_id', 'string'),
    ('task_id', 'string'),
    ('sequence_entry_type', 'int32'),
    ('program_name', 'string'),
    ('program_path', 'string'),  # FILE REFERENCE
    ('command_line', 'string'),
    ('unknown_string', 'string'),
    ('user_data_1', 'string'),
    ('user_data_2', 'string'),
    ('user_data_3', 'string'),
    ('user_data_4', 'string'),
    ('user_data_5', 'string'),
    ('user_data_6', 'string'),
    ('user_data_7', 'string'),
    ('user_data_8', 'string'),
    ('user_data_9', 'string'),
    ('user_data_10', 'string'),
    ('cycle_text', 'string'),
)


NAIBOXINFO = (
    ('delay_time_(min.)', 'double'),
    ('run_time_for_data_collection_(min.)', 'double'),
    ('total_run_time_(min.)', 'double'),
    ('sampling_rate_(pts/sec.)', 'double'),
    ('sampling_code', 'int32'),
    ('a/d_voltage_range', 'int32'),
    ('data_collection_channel', 'int32'),
    ('store_all_data_flag_(i.e._run_time_=_total_time)', 'BOOL'),
    ('autosampler_injection_source', 'int32'),
    ('use_bipolar_mode', 'BOOL'),
)


INSTRUMENT_DATA_HEADER = (
    ('data_header', DATA_HEADER),
    ('instrument_header_text', 'string'),
    ('instrument_type', 'INST_TYPE'),
    ('number_of_channels_for_data_collection', 'int32'),
    ('instrument_text', 'string'),
)

INSTRUMENT_METHOD_STRUCTURE = (
    ('instrument_data_header', INSTRUMENT_DATA_HEADER),
    #('intelligent_interface_parameters', NAIBOXINFO),
    #('instrument_configuration_parameters', INST_CONFIG),
    #('real-time_plot_parameters', array<PINFO>),
    #('link_parameters_array', <LINKPARM_INFO>'),
)

def parse_simple_types(specification, file_):
    """Parse simple types"""
    #print("PARSE")
    output = {}
    for name, type_ in specification:
        #print("\nPARSE SPEC", name, type_, "AT", file_.tell())
        if type_ == 'string':
            size = unpack('>i', file_.read(4))[0]
            format_ = '>{}s'.format(size)
            if size % 4 != 0:
                format_ += 'x' * (4 - size % 4)
            bytes_ = file_.read(calcsize(format_))
            #print("Read {} bytes of string".format(len(bytes_)))
            value = unpack(format_, bytes_)[0].decode('ascii')
        elif type_ == 'double':
            # Appearently, in this serialization, the two groups of 4
            # bytes are in reversed order, so special case it
            first_four = file_.read(4)
            last_four = file_.read(4)
            value = unpack('>d', last_four + first_four)[0]
        elif type_ == 'pnw_date':
            unix_time = unpack('>i', file_.read(4))[0]

            # We do not fully understand the time stamp, FIXME
            #import datetime
            #print(
            #    datetime.datetime.fromtimestamp(
            #        unix_time
            #    ).strftime('%Y-%m-%d %H:%M:%S')
            #)
            timestamp = unpack('>bbhbbbb', file_.read(8))
            #timestamp = unpack('>hBBBBBB', file_.read(8))
            #print("TIMESTAMP", timestamp)
            #file_.read(11)

            # Just save unix time for now
            value = unix_time
        elif isinstance(type_, tuple):
            value = parse_simple_types(type_, file_)
        else:
            # struct parseable type
            format_ = TYPE_TRANSLATION[type_]
            value = unpack(format_, file_.read(calcsize(format_)))[0]
        #print("VALUE IS", repr(value))
        output[name] = value
    return output


def parse_array(type_, file_):
    """Parse an array

    Args:
        type_ (str or numpy.dtype): The numpy data type of the array data
        file_ (file): The file object to read from

    Returns:
        numpy.array: The parsed array
    """
    number_of_points = unpack('>i', file_.read(4))[0]
    array = fromfile(file_, dtype=type_, count=number_of_points)
    return array


class Raw:
    """Raw file FIXME"""

    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'rb') as file_:
            # File starts with a file header
            self.file_header = parse_simple_types(FILE_HEADER, file_)

            # Then comes a raw data header that starts with a data header
            self.raw_data_header = parse_simple_types(RAW_DATA_HEADER, file_)

            self.ad_header = parse_simple_types(ADHEADER, file_)

            # Sequence FIXME
            #file_.read(8)
            #print("\n\n\n##############################")
            self.seq_description = parse_simple_types(SEQ_DESCRIPTION, file_)

            #print(file_.tell())
            self.raw_data_points = parse_array('>i4', file_)

            #print("\n\n\n##############################")
            #self.instrument_method_structure = parse_simple_types(
            #    INSTRUMENT_METHOD_STRUCTURE, file_,
            #)



def module_demo():
    """Module demon"""
    filepath = ('/home/kenni/surfcat/setups/307-059-largeCO2MEA/'
                'GC_parsing/Test8_Carrier=Ar_70mLH2_26mLCO_60C_Att'
                '=-2_NoRamp.raw')
    raw_file = Raw(filepath)
    print(raw_file)

if __name__ == '__main__':
    module_demo()
