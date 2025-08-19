from api.api_caller import APICaller
from api.modules.ocr import ocr_module
from api.modules.ie import ie_module

api_caller = APICaller()

api_caller.register_module(ocr_module)
api_caller.register_module(ie_module)
