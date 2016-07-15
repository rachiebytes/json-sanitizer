from jsonschema import validate
import datetime
from dateutil import parser
import rfc3339
import pprint


# TODO: other things than properties

class JSONSchemaSanitizer():

    def __init__(self, schema=None):
        self.schema = schema
        self.primitive_types = {
            'array': self.format_array,
            'boolean': self.format_bool,
            'integer': self.format_int,
            'null': self.format_null,
            'number': self.format_number,
            'object': self.format_dict,
            'string': self.format_string
        }   
        self.string_formats = {
            'date-time': self.format_date_time,
            'default': self.format_default,
            'email': self.format_email,
            'hostname': self.format_hostname,
            'ipv4': self.format_ipv4,
            'ipv6': self.format_ipv6,
            'reg-ex' : self.format_regex,
            'uri': self.format_uri
        }
        
    """
    Main function to be called.
    
        dirty_object: The object you want sanitized and formatted. The 
            keys should match the keys found in the JSON Schema properties.
        
        Returns the object with the values matching the JSON Schema
        properties keys and their types, formats, etc.
    """
    def sanitize_properties(self, dirty_object):
        sanitized_object = {}

        properties = self.schema.get('properties', {})

        for property_name in dirty_object:
        
            dirty_value = dirty_object[property_name]
            schema_property_object = properties.get(property_name, None)
            
            sanitized_value = self.sanitize_value(dirty_value, schema_property_object)
            sanitized_object[property_name] = sanitized_value

        # USE THE VALIDATE LIBRARY?
        validate(sanitized_object, self.schema)

        return sanitized_object


    """
    Methods to direct the value on how to be sanitized.
    
        dirty_value: The dirty value that needs to be sanitized
            to match the type and format in the JSON Schema.
        schema_property_object: The schema property object you
            want your value to abide to.
            
        Returns the the value with the correct type and format.
    """
    def sanitize_value(self, dirty_value, schema_property_object):
        type = schema_property_object.get('type', None)
        primitive_type_func = self.primitive_types.get(type, KeyError(type + ' is not a primitive value type.'))
        return primitive_type_func(dirty_value, schema_property_object)


    ########################################################################
    #
    # PRIMITIVE TYPE METHODS
    #
    ########################################################################

    """
    Methods for a JSON Schema property with type array.
    """
    # TODO:
        # unique items
        # handle arrays that can contain multiple primitive types
        # handle multi-dimensional arrays
        # if the value type is a string, check if it is comma separated or another delimiter
    def format_array(self, value, schema_property_object):
        value_type = type(value)
        items, array_item_type = self.get_array_information(schema_property_object)
        
        if value_type is list:
            return self._format_value_type_list(value, items, array_item_type)           
        else:
            if array_item_type is not None:
                primitive_type_func = self.primitive_types.get(array_item_type, KeyError(array_item_type + ' is not a primitive value type.'))
                return [primitive_type_func(value, items)]
            else:
                return [value]

    def get_array_information(self, items_object):
        items = items_object.get('items', {})
        array_item_type = items.get('type', None)
        return items, array_item_type

    def _format_value_type_list(self, value, items_information, array_item_type=None):
        if array_item_type is None:
            return value
        else:
            primitive_type_func = self.primitive_types.get(array_item_type, KeyError(array_item_type + ' is not a primitive value type.'))
            return [primitive_type_func(x, items_information) for x in value]
             
    """
    Methods for a JSON Schema property with type bool.
    """
    def format_bool(self, value, schema_property_object=None):
        if type(value) is str:
            value = value.lower()
        
        false_values = ['f', 'false', False]
        true_values = ['t', 'true', True]

        if value in false_values:
            return False
        elif value in true_values:
            return True
        else:
            return None

    """
    Method for a JSON Schema property with type integer.
    """
    def format_int(self, value, schema_property_object=None):
        try:
            integer = int(value)
            return integer
        except ValueError:
            print 'Could not convert ' + value + ' to an int.'
            return None

    """
    Method for a JSON Schema property with type number.
    """ 
    def format_number(self, value, schema_property_object=None):
        try:
            floating_point = float(value)
            return floating_point
        except ValueError:
            print 'Could not convert ' + value + ' to a number.'
            return None

    """
    Methods for a JSON Schema property with type null.
    """
    def format_null(self, value=None, schema_property_object=None):
        return None

    """
    Methods for a JSON Schema property with type object.
    """
    def format_dict(self, value, schema_property_object=None):
        # TODO
        pass

    """
    Methods for a JSON Schema property with type string.
        
        value: The value you want sanitized to a string with
        the correct format that is indicated in the schema property.
        
        schema_property_object (optional): The schema property object
            you want the string value to abide to. If the object is 
            missing the format key or if the object  is not passed then 
            default sanitization is the value wrapped in a string.
    """
    def format_string(self, value, schema_property_object={}): 
        # TODO: enum stuff
        format = self.get_string_information(schema_property_object)
        format_func = self.string_formats.get(format,
                self.string_formats.get('default'))
        return format_func(value)

    def get_string_information(self, item_object={}):
        format = item_object.get('format', None)
        return format


    ########################################################################
    #
    # STRING FORMAT METHODS
    #
    ########################################################################


    """
    Method to format date-time.

        Little-Endian format is not expected. If you know that will be the format
        then set little_endian=True

        value: The value you want santized to a date-time string.

        little_endian: Indicates the input value is in little endian format.

        Returns an ISO date-time in a string. i.e. 1999-06-01T00:00:00-04:00
    """
    def format_date_time(self, value, little_endian=False):
        # TODO: a func that switches month/day if little_endian is true
        o = parser.parse(value)
        date = rfc3339.rfc3339(o)
        return date


    """
    Method for the default string format.

        Returns a string encoded in unicode.
    """
    def format_default(self, value):
       return unicode(value)

    """
    Method to format an email.
    """
    def format_email(self, value):
        # TODO
        pass

    """
    Method to format an hostname.
    """
    def format_hostname(self, value):
        # TODO
        pass

    """
    Method to format an ipv4.
    """
    def format_ipv4(self, value):
        # TODO
        pass

    """
    Method to format an ipv6.
    """
    def format_ipv6(self, value):
        # TODO
        pass

    """
    Method to format reg-ex.
    """
    def format_regex(self, value):
        # TODO
        pass

    """
    Method to format uri.
    """
    def format_uri(self, value):
        # TODO
        pass

# <3,
# rachiebytes
