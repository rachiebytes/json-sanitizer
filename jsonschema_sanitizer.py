import json
from jsonschema import validate
import datetime
from dateutil import parser
import rfc3339
import logging


class JSONSchemaSanitizer():

    def __init__(self, schema=None):
        self.schema = schema
        self.primitive_types = {
            'array': self.format_array,
            'boolean': self.format_bool,
            'integer': self.format_int,
            'null': self.format_null,
            'number': self.format_number,
            'object': self.format_object,
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
        self.non_primitive_types = self._create_non_primitive_types_store()
        
    ########################################################################
    # MARK: Init methods
    ########################################################################
    
    def _create_non_primitive_types_store(self):
        x = {}
        definitions = self.schema.get(u'definitions', [])
        for definition in definitions:
            properties = definitions[definition].get('properties', {})
            definition_type = properties.get('type', {}).get('enum', [])
            for item in definition_type:
                path = '#/definitions/' + definition
                x[item] = self.get_reference_value(path)
        return x

    ########################################################################
    # MARK: Main methods
    ########################################################################

    def sanitize_properties(self, dirty_object):
        """
        Main function to be called.
        
        Params:
            dirty_object: The object you want sanitized and formatted. The 
                keys should match the keys found in the JSON Schema properties.
            
        Returns the object with the values matching the JSON Schema
        properties keys and their types, formats, etc.
        """
        sanitized_object = self.format_object(dirty_object, self.schema)

        if sanitized_object:
            # LOGGING
            LOG_FILENAME = '{:%Y-%m-%d}'.format(datetime.datetime.now()) + '-extraction.log'
            logging.basicConfig(filename=LOG_FILENAME,level=logging.ERROR)
            
            try:
                validate(sanitized_object, self.schema)
                return sanitized_object
            except:
                current_time = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
                logging.error(current_time + ' ' + str(sanitized_object))


    ########################################################################
    # MARK: Primitive type methods
    ########################################################################

    def format_array(self, value, schema_property_object):
        """
        Method for a JSON Schema property with type array.
        """
        value_by_type = type(value)
        items = schema_property_object.get('items', {})
        array_item_type = items.get('type', None)
        
        if value_by_type is list:
            return self._format_value_type_list(value, schema_property_object, items, array_item_type)
        elif array_item_type:
                primitive_type_func = self.primitive_types.get(array_item_type, KeyError(array_item_type + ' is not a primitive value type.'))
                return [primitive_type_func(value, items)]
        else:
            return [value]

    def _format_value_type_list(self, value, schema_property_object, items, array_item_type=None):
        one_of = True if items.get('oneOf', None) else None

        if one_of:
            return self._one_of(value) # <--revisit this
        elif array_item_type is None:
            return value
        else:
            primitive_type_func = self.primitive_types.get(array_item_type, KeyError(array_item_type + ' is not a primitive value type.'))
            return [primitive_type_func(x, items) for x in value]
    
    def format_bool(self, value, schema_property_object=None):
        """
        Methods for a JSON Schema property with type bool.
        """
        if type(value) is str:
            value = value.lower()

        false_values = ['f', 'false', False]
        true_values = ['t', 'true', True]

        if value in false_values:
            return False
        elif value in true_values:
            return True

    def format_int(self, value, schema_property_object=None):
        """
        Method for a JSON Schema property with type integer.
        """
        try:
            integer = int(value)
            return integer
        except ValueError:
            print 'Could not convert ' + value + ' to an int.'


    def format_number(self, value, schema_property_object=None):
        """
        Method for a JSON Schema property with type number.
        """
        try:
            floating_point = float(value)
            return floating_point
        except ValueError:
            print 'Could not convert ' + value + ' to a number.'

    def format_null(self, value=None, schema_property_object=None):
        """
        Method for a JSON Schema property with type null.
        """
        return None


    def format_object(self, object, schema_property_object=None):
        """
        Method for a JSON Schema property with type object.
        """
        sanitized_object = {}
        
        
        # SPECIAL TO DEFINITIONS
        definition_type = object.get(u'type', None)
        if definition_type:
            schema_property_object = self.non_primitive_types.get(definition_type, None)
            if schema_property_object is None:
                return
            del object['type']
        #########################

        for property in object:
            dirty_value = object[property]
            spo = schema_property_object[u'properties'][property]
            
            ref = spo.get(u'$ref', None)
            if ref:
                spo = self.get_reference_value(ref)
            enum = spo.get(u'enum', None)
            if enum:
                value = self._enum_check(dirty_value, enum)
                if value:
                    sanitized_object[property] = dirty_value
                    continue
                else:
                    break
    
            type = spo[u'type']
            primitive_type_func = self.primitive_types.get(type, KeyError(type + ' is not a primitive value type.'))
            sanitized_value = primitive_type_func(dirty_value, spo)
            if sanitized_value:
                sanitized_object[property] = sanitized_value
        
        if sanitized_object:
            if definition_type:
                sanitized_object['type'] = definition_type
            
            required_keys = schema_property_object.get(u'required', None)
            if required_keys:
                for key in required_keys:
                    key_exists = sanitized_object.get(key, None)
                    if not key_exists:
                        sanitized_object = {}
            return sanitized_object

    def format_string(self, value, schema_property_object={}):
        """
        Method for a JSON Schema property with type string.
            
        Params:
            value: The value you want sanitized to a string with
            the correct format that is indicated in the schema property.
            
            schema_property_object (optional): The schema property object
                you want the string value to abide to. If the object is 
                missing the format key or if the object is not passed then
                default sanitization is the value wrapped in a string.
        """
        format = schema_property_object.get('format', None)
        format_func = self.string_formats.get(format,
                self.string_formats.get('default'))
        return format_func(value)

    ########################################################################
    # MARK: String format methods
    ########################################################################

    def format_date_time(self, value, little_endian=False):
        """
        Method to format date-time.

        Params:
            value: The value you want santized to a date-time string.
            little_endian: Indicates the input value is in little endian format.

        Little-Endian format is not expected. If you know that will be the format
        then set little_endian=True
        
        Returns an ISO date-time in a string. i.e. 1999-06-01T00:00:00-04:00
        """
        # TODO: switch month/day if little_endian is true
        o = parser.parse(value)
        date = rfc3339.rfc3339(o)
        return date

    def format_default(self, value):
        """
        Method for the default string format.

        Returns a string encoded in unicode.
        """
        return unicode(value)

    def format_email(self, value):
        """
        TODO: Method to format an email.
        """
        pass

    def format_hostname(self, value):
        """
        TODO: Method to format an hostname.
        """
        pass

    def format_ipv4(self, value):
        """
        TODO: Method to format an ipv4.
        """
        pass

    def format_ipv6(self, value):
        """
        TODO: Method to format an ipv6.
        """
        pass

    def format_regex(self, value):
        """
        TODO: Method to format reg-ex.
        """
        pass

    def format_uri(self, value):
        """
        TODO: Method to format uri.
        """
        pass

    ########################################################################
    # MARK: allOf, anyOf, oneOf, not
    ########################################################################
    
    # http://json-schema.org/latest/json-schema-validation.html#anchor88
    def _one_of(self, one_of_array):
        build_array = []
        for item in one_of_array:
            cleaned_item = self.format_object(item) # visit this, type might be different
            if cleaned_item:
                build_array.append(cleaned_item)
        return build_array
    
    ########################################################################
    # MARK: Reference path methods
    ########################################################################

    def get_reference_value(self, path, value=None):
        path_split = path.split('/')
        if(len(path_split) < 1):
            return
        if '#' in path_split[0]:
            return self.get_value_from_json_pointer_path(path_split)

    # TODO https://tools.ietf.org/html/rfc6901
    def get_value_from_json_pointer_path(self, path):
        if len(path) > 1:
            del path[0] # this value is #, which indicates the start of the json
        value = self.schema
        for key in path:
            value = value.get(key)
        return value

    ########################################################################
    # MARK: Utils
    ########################################################################
    
    def _enum_check(self, value, enum_mapping):
        if value in enum_mapping:
            return True
        else:
            return False

# <3, rachiebytes
