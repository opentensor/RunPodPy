# The MIT License (MIT)
# Copyright © 2022 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

from argparse import ArgumentParser

from munch import Munch
from ruamel.yaml import YAML

import os
yaml = YAML()

class Config ( Munch ):
    """
    Implementation of the config class
    """
    def __init__(self, loaded_config = None ):
        super().__init__()
        if loaded_config:
            raise NotImplementedError('Function load_from_relative_path is not fully implemented.')

    def __repr__(self) -> str:
        return self.__str__()
    
    def __str__(self) -> str:
        return "\n" + yaml.dump(self.toDict())

    def to_string(self, items) -> str:
        """ Get string from items
        """
        return "\n" + yaml.dump(items.toDict())

    def update_with_kwargs( self, kwargs ):
        """ Add config to self
        """
        for key,val in kwargs.items():
            self[key] = val

class InvalidConfigFile(Exception):
        """ In place of YAMLError
        """

def config_builder( parser: ArgumentParser = None, strict: bool = False ) -> Config:
        r""" Translates the passed parser into a nested config.
        Args:
            parser (argparse.Parser):
                Command line parser object.
            strict (bool):
                If true, the command line arguments are strictly parsed.
        Returns:
            config (runpodpy.Config):
                Nested config object created from parser arguments.
        """
        if parser == None:
            parser = ArgumentParser()

        # Optionally add config specific arguments
        try:
            parser.add_argument('--config', type=str, help='If set, defaults are overridden by passed file.')
        except:
            # this can fail if the --config has already been added.
            pass
        try:
            parser.add_argument('--strict',  action='store_true', help='''If flagged, config will check that only exact arguemnts have been set.''', default=False )
        except:
            # this can fail if the --config has already been added.
            pass

        # 1.1 Optionally load defaults if the --config is set.
        try:
            config_file_path = str(os.getcwd()) + '/' + vars(parser.parse_known_args()[0])['config']
        except Exception as e:
            config_file_path = None

        # 2. Optionally check for --strict, if stict we will parse the args strictly.
        strict = parser.parse_known_args()[0].strict
                        
        if config_file_path != None:
            config_file_path = os.path.expanduser(config_file_path)
            try:
                with open(config_file_path) as f:
                    params_config = yaml.safe_load(f)
                    print('Loading config defaults from: {}'.format(config_file_path))
                    parser.set_defaults(**params_config)
            except Exception as e:
                print('Error in loading: {} using default parser settings'.format(e))

        # 2. Continue with loading in params.
        if not strict:
            params = parser.parse_known_args()[0]
        else:
            params = parser.parse_args()
        _config = Config()

        # Splits params on dot syntax i.e machine.podName          
        for arg_key, arg_val in params.__dict__.items():
            split_keys = arg_key.split('.')
            head = _config
            keys = split_keys
            while len(keys) > 1:
                if hasattr(head, keys[0]):
                    head = getattr(head, keys[0])  
                    keys = keys[1:]   
                else:
                    head[keys[0]] = Config()
                    head = head[keys[0]] 
                    keys = keys[1:]
            if len(keys) == 1:
                head[keys[0]] = arg_val

        return _config
