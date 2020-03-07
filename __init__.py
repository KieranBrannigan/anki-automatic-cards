import os


#Check if MIA dictionary installed
addon_folder = os.path.dirname(__file__)
MIA_dictionary = os.path.isdir(os.path.join(addon_folder,'..','1655992655'))

if MIA_dictionary:
    from . import has_mia_dict