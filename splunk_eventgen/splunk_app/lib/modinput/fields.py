'''
Copyright (C) 2005 - 2018 Splunk Inc. All Rights Reserved.
'''
import json
import re


class FieldValidationException(Exception):
    pass


class Field(object):
    """
    This is the base class that should be used to create field validators. Sub-class this and override to_python if you need custom validation.
    """

    DATA_TYPE_STRING = 'string'
    DATA_TYPE_NUMBER = 'number'
    DATA_TYPE_BOOLEAN = 'boolean'

    def get_data_type(self):
        """
        Get the type of the field.
        """

        return Field.DATA_TYPE_STRING

    def __init__(self, name, title, description, required_on_create=True, required_on_edit=False):
        """
        Create the field.

        Arguments:
        name -- Set the name of the field (e.g. "database_server")
        title -- Set the human readable title (e.g. "Database server")
        description -- Set the human readable description of the field (e.g. "The IP or domain name of the database server")
        required_on_create -- If "true", the parameter is required on input stanza creation.
        required_on_edit -- If "true", the parameter is required on input stanza modification.

        Default values for required_on_create and required_on_edit match the
        documented behavior at http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModInputsScripts.
        """

        # Note: there is no distinction between a None value and blank value,
        # as modular input UIs does not recognize such a distinction.
        if name is None or len(name.strip()) == 0:
            raise ValueError("The name parameter cannot be empty.")

        if title is None or len(title.strip()) == 0:
            raise ValueError("The title parameter cannot be empty.")

        if description is None or len(description.strip()) == 0:
            raise ValueError("The description parameter cannot be empty.")

        self.name = name
        self.title = title
        self.description = description
        self.required_on_create = required_on_create
        self.required_on_edit = required_on_edit

    def to_python(self, value):
        """
        Convert the field to a Python object. Should throw a FieldValidationException if the data is invalid.

        Arguments:
        value -- The value to convert
        """

        # No standard validation here; the modular input framework handles empty values.
        return value

    def to_string(self, value):
        """
        Convert the field to a string value that can be returned. Should throw a FieldValidationException if the data is invalid.

        Arguments:
        value -- The value to convert
        """

        return str(value)


class BooleanField(Field):

    def to_python(self, value):
        Field.to_python(self, value)

        if value in [True, False]:
            return value

        elif str(value).strip().lower() in ["true", "t", "1"]:
            return True

        elif str(value).strip().lower() in ["false", "f", "0"]:
            return False

        raise FieldValidationException("The value of '%s' for the '%s' parameter is not a valid boolean" % (str(value), self.name))

    def to_string(self, value):

        if value == True:
            return "1"

        elif value == False:
            return "0"

        return str(value)

    def get_data_type(self):
        return Field.DATA_TYPE_BOOLEAN


class DelimitedField(Field):

    def __init__(self, name, title, description, delim, required_on_create=True, required_on_edit=False):
        super(DelimitedField, self).__init__(name, title, description, required_on_create, required_on_edit)
        self._delim = delim

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            try:
                tmp = value.split(self._delim)
                return tmp
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None

    def to_string(self, value):

        if value is not None:
            return str(value)

        return ""

    def get_data_type(self):
        return Field.DATA_TYPE_STRING


class DurationField(Field):
    """
    The duration field represents a duration as represented by a string such as 1d for a 24 hour period.

    The string is converted to an integer indicating the number of seconds.
    """

    DURATION_RE = re.compile("(?P<duration>[0-9]+)\s*(?P<units>[a-z]*)", re.IGNORECASE)

    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800

    UNITS = {
             'w': WEEK,
             'week': WEEK,
             'd': DAY,
             'day': DAY,
             'h': HOUR,
             'hour': HOUR,
             'm': MINUTE,
             'min': MINUTE,
             'minute': MINUTE,
             's': 1
             }

    def to_python(self, value):
        Field.to_python(self, value)

        # Parse the duration
        m = DurationField.DURATION_RE.match(value)

        # Make sure the duration could be parsed
        if m is None:
            raise FieldValidationException("The value of '%s' for the '%s' parameter is not a valid duration" % (str(value), self.name))

        # Get the units and duration
        d = m.groupdict()

        units = d['units']

        # Parse the value provided
        try:
            duration = int(d['duration'])
        except ValueError:
            raise FieldValidationException("The duration '%s' for the '%s' parameter is not a valid number" % (d['duration'], self.name))

        # Make sure the units are valid
        if len(units) > 0 and units not in DurationField.UNITS:
            raise FieldValidationException("The unit '%s' for the '%s' parameter is not a valid unit of duration" % (units, self.name))

        # Convert the units to seconds
        if len(units) > 0:
            return duration * DurationField.UNITS[units]
        else:
            return duration

    def to_string(self, value):
        return str(value)


class FloatField(Field):

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            try:
                return float(value)
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None

    def to_string(self, value):

        if value is not None:
            return str(value)

        return ""

    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER


class IntegerField(Field):

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            try:
                return int(value)
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None

    def to_string(self, value):

        if value is not None:
            return str(value)

        return ""

    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER


class IntervalField(Field):
    '''Class for handling Splunk's "interval" field, which typically accepts
    an integer value OR a cron-style string. Note that this means that the
    data type returned is a string, so the modular input must handle conversion
    of this string to an integer at runtime.'''

    # Accepted cron field formats:
    #    Asterisk:      *  (equivalent to first-last range)
    #    Lists:         1,2,3,4,5
    #    Ranges:        1-60
    #
    # and combinations of the above:
    #
    #    Ranges followed by steps:    0-23/2
    #    Asterisks followed by steps:    */2
    #
    # Note that we don't check explicitly for correct numeric values for each
    # cron field.

    cron_rx = re.compile('''
        (
             \d{1,2}                    # A digit.
            |\d{1,2}-\d{1,2}            # A range.
            |(\d{1,2},)+\d{1,2}         # A list of digits.
            |\d{1,2}-\d{1,2}/\d{1,2}    # A range followed by a step.
            |\*                         # The asterisk character.
            |\*/\d{1,2}                 # An asterisk followed by a step.
        )
        ''',
        re.VERBOSE
    )

    def to_python(self, value):

        try:
            # Try parsing the string as an integer.
            tmp = int(value)
            return value
        except ValueError:
            # Try parsing the string as a cron schedule.
            if self.parse_cron(value):
                return value

        raise FieldValidationException("The value of '{}' for the '{}' parameter is not a valid value".format(value, self.name))

    def get_data_type(self):
        return Field.DATA_TYPE_STRING

    def parse_cron(self, value):
        '''Check for valid cron string.'''

        fields = value.split()
        if len(fields) == 5 and all([self.cron_rx.match(i) for i in fields]):
            return True
        return False


class JsonField(Field):

    def to_python(self, value):
        Field.to_python(self, value)

        try:
            return json.loads(value)
        except (TypeError, ValueError):
            raise FieldValidationException("The value of '%s' for the '%s' parameter is not a valid JSON object" % (str(value), self.name))

    def to_string(self, value):
        return str(value)

    def get_data_type(self):
        return Field.DATA_TYPE_STRING


class ListField(Field):

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            return value.split(",")
        else:
            return []

    def to_string(self, value):

        if value is not None:
            return ",".join(value)

        return ""


class RangeField(Field):

    def __init__(self, name, title, description, low, high, required_on_create=True, required_on_edit=False):
        super(RangeField, self).__init__(name, title, description, required_on_create, required_on_edit)
        self.low = low
        self.high = high

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            try:
                tmp = int(value)
                if tmp >= self.low and tmp <= self.high:
                    return tmp
                else:
                    raise FieldValidationException("Value out of range.")
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None

    def to_string(self, value):

        if value is not None:
            return str(value)

        return ""

    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER


class RegexField(Field):

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            try:
                return re.compile(value)
            except Exception as e:
                raise FieldValidationException(str(e))
        else:
            return None

    def to_string(self, value):

        if value is not None:
            return value.pattern

        return ""


class SeverityField(Field):

    # Note: We ignore "FATAL" severity since Python's logging assigns it the
    # same value as "CRITICAL".
    SEVERITIES = {'DEBUG': 10,
                  'INFO': 20,
                  'WARN': 30,
                  'ERROR': 40,
                  'CRITICAL': 50}

    SEVERITIES_BY_INT = {v: k for k, v in SEVERITIES.iteritems()}

    def to_python(self, value):

        try:
            if value in SeverityField.SEVERITIES:
                return SeverityField.SEVERITIES[value]
        except AttributeError:
            # Did not receive a string for some reason.
            pass

        raise FieldValidationException("The value of '{}' for the '{}' parameter is not a valid value".format(value, self.name))

    def to_string(self, value):
        if value in SeverityField.SEVERITIES_BY_INT:
            return SeverityField.SEVERITIES_BY_INT[value]
        else:
            raise ValueError('Invalid value provided for severity.')

    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER