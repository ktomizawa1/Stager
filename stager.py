from zebra.io import unity
from zebra import util
import os
import argparse
import time
import re

os.system("")
CRED = '\033[31m'
CGREEN = '\033[32m'
CYELLOW = '\033[33m'
CEND = '\033[0m'

STAGE_FILENAME = "__stage_config.txt"
STAGING_FILES_DIR = "C:\evt\From Customer Original - Copy"
PRINTER_PID           = 0x01D7
ALLCV_FILENAME        = "__allcv"
CONFIGURATION_FILENAME= "__configuration"

class ActionBase:
    def execute(self, env):
        pass

    # Prior to any action being executed, all actions are validated by running this
    def validate(self, env):
        pass

    def serialize(self):
        return ""

class ActionDefault(ActionBase):
    NAME = "Default"

    def execute(self, env):
        print("Defaulting printer")
        env.printer.send(b'! U1 setvar "file.delete" "*.*"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.WML"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.CPF"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.PCX"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.CFG"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.TXT"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.CSF"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.NRD"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.PRF"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.WKF"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.LBL"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.WML"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.TTF"\r\n')
        env.printer.send(b'! U1 setvar "file.delete" "*.BMP"\r\n')
        time.sleep(5)
        serial = env.printer.getvar(b'device.unique_id')
        env.printer.send(b'~PM' + serial + b'\r\n')
        env.printer.device_reset(timeout=180)
        time.sleep(30)

        # Check for files in E: 
        e_files = env.printer.get_directory()
        if len(e_files) > 0:
            print(CRED + "E: Drive not clear:" + CEND)
            for e_file in e_files:
                print('\t' + e_file[0].decode())

    def serialize(self):
        return self.NAME

def isFWfile(filename):
    reg = re.search(r"SP\d+-\d{6}\S\.ZPL", filename.upper())
    if (reg == None):
        return False
    else:
        return True

class ActionDownload(ActionBase):
    NAME = "Download"
    def __init__(self, filename):
        self.filename = filename
    
    def validate(self, env):
        if not os.path.isfile(os.path.join(env.staging_dir, self.filename)):
            print(CRED + "ERROR: File does not exists: " + self.filename)
            raise FileNotFoundError("File does not exist: " + self.filename) 

    def execute(self, env):
        print("Downloading file: {}".format(self.filename))
        env.printer.send_file(os.path.join(env.staging_dir, self.filename))
        if (isFWfile(self.filename)):
            env.printer.device_reset(timeout=180)
            time.sleep(30)
        else:
            time.sleep(0.5)

    def serialize(self):
        return "{}: {}".format(self.NAME, self.filename)

class ActionGetALLCV(ActionBase):
    NAME = "GetALLCV"

    def execute(self, env):
        print("Retrieving ALLCV")
        env.printer.send(b'! U1 getvar "allcv"\r\n')
        allcv = env.printer.collect_until(b'""', 10)
        
        # Use new filename if base filename already exists
        config_filename = os.path.join(env.staging_dir, ALLCV_FILENAME + ".txt")
        config_filename_count = 0
        while(os.path.isfile(config_filename)):
            config_filename_count += 1
            config_filename = os.path.join(env.staging_dir, "{}{}.txt".format(ALLCV_FILENAME,config_filename_count))

        with open(config_filename, "wb") as output_allcv:
            output_allcv.write(allcv) 

    def serialize(self):
        return self.NAME

class ActionGet2Key(ActionBase):
    NAME = "Get2Key"

    def execute(self, env):
        print("Retreiving 2KEY")
        env.printer.send(b'\x1bI\r\n')
        printer_configuration = env.printer.collect(2.5)
       
        # Use new filename if base filename already exists
        config_filename = os.path.join(env.staging_dir, CONFIGURATION_FILENAME + ".txt")
        config_filename_count = 0
        while(os.path.isfile(config_filename)):
            config_filename_count += 1
            config_filename = os.path.join(env.staging_dir, "{}{}.txt".format(CONFIGURATION_FILENAME,config_filename_count))

        with open(config_filename, "wb") as output_configuration:
            output_configuration.write(printer_configuration)

    def serialize(self):
        return self.NAME

class ActionReset(ActionBase):
    NAME = "Reset"

    def execute(self, env):
        print("Rebooting printer...")
        time.sleep(10) # Allow printer to process any commands still in buffer
        env.printer.device_reset(timeout=180)
        time.sleep(30)
    
    def serialize(self):
        return self.NAME

class ActionTestSettings(ActionBase):
    NAME = "TestSettings"

    def parse_config_sgd(self, filename):
        sgd_ref = []
        # TODO: Check if there are duplicate set SGDs
        with open(filename) as config_file:
            lines = config_file.readlines()
            line_num = 0;
            for line in lines:
                line_num += 1
                if len(line) > 1:
                    try:
                        re_result = re.search(r'!\s+U1\s+setvar\s+"(.*?)" "(.*?)"', line)
                        sgd_ref.append([re_result.group(1), re_result.group(2)])
                    except:
                        print("Failed to parse line {}: {}".format(line_num, line))
        
        return sgd_ref

    def execute(self, env):
        print("Testing Settings: ")

        # Get list of all downloaded files
        downloadFiles = []
        for action in env.actions:
            try:
                downloadFiles.append(action.filename)
            except AttributeError:
                # Actions that don't have a filename will throw an AttributeError
                pass

        # Find config file and parse it
        configsgd_file = ""
        for downloadFile in downloadFiles:
            if ".sgd" in downloadFile:
                configsgd_file = downloadFile
                break
        if configsgd_file != "":
            sgds = self.parse_config_sgd(os.path.join(env.staging_dir, configsgd_file))
        
        # Test each SGD found in config file
        sgd_success = []
        sgd_fail = []
        for sgd in sgds:
            result = env.printer.getvar(sgd[0])
            if ("password" in sgd[0]):
                print(CYELLOW + "\tSkipping {}:{}".format(sgd[0],result) + CEND)
                sgd_success.append(sgd)
            elif (result != sgd[1]):
                sgd_fail.append(sgd)
                print(CRED + "\tFAIL: {} \n\t\tExpected:{} \n\t\tActual  :{}".format(sgd[0] ,sgd[1], result) + CEND)
            else:
                sgd_success.append(sgd)
                print("\tOK: {}:{}".format(sgd[0] , result))
        
        # Generate and save config.set
        configset_filename = os.path.join(env.staging_dir, "__config.set")
        with open(configset_filename, "w") as output_configuration:
            for sgd in sgd_fail:
                output_configuration.write("! U1 setvar \"{}\" \"{}\"\n".format(sgd[0], sgd[1]))

        # Generate and save config.sgd
        configsgd_filename = os.path.join(env.staging_dir, "__config.sgd")
        with open(configsgd_filename, "w") as output_configuration:
            for sgd in sgd_success:
                output_configuration.write("! U1 setvar \"{}\" \"{}\"\n".format(sgd[0], sgd[1]))

    def serialize(self):
        return self.NAME

class ActionEDriveDiff(ActionBase):
    NAME = "EDriveDiff"

    def execute(self, env):
       env.printer.bitbucket(1)
       files = env.printer.get_directory()
       newFiles = []
       for efile in files:
           if efile not in env.currentFiles:
               newFiles.append(efile)
       
       print("File diff:")
       for newFile in newFiles:
           print("\t{} {}".format(newFile[0].decode(), newFile[1] ))

       env.currentFiles = files

    def serialize(self):
        return self.NAME

class ActionFactory:
    
    def __init__(self):
        self.actionList = [
                ActionDefault,
                ActionDownload,
                ActionGetALLCV,
                ActionGet2Key,
                ActionReset,
                ActionTestSettings,
                ActionEDriveDiff,
                ]

    # NEED TO IMPROVE THIS
    def create(self, inputString):
        for actionType in self.actionList:
            print (actionType.NAME)
            if actionType.NAME in inputString:
                return actionType()

    def createFromDir(self, dirPath):
        actionList = []
        
        filesInDir = get_files(dirPath)
        for fileToStage in filesInDir:
            if (isFWfile(fileToStage)):
                # Download fw first
                actionList.insert(0, ActionDownload(fileToStage))
                actionList.insert(1, ActionDefault())
            else:
                actionList.append(ActionDownload(fileToStage))
                
        # Throw in some default actions for free :D
        actionList.append(ActionReset())
        actionList.append(ActionTestSettings())
        actionList.append(ActionGetALLCV())
        actionList.append(ActionGet2Key())

        return actionList


def get_files(path_to_walk):
    ret = []
    for (dirpath, dirnames, filenames) in os.walk(path_to_walk):
        path = dirpath.removeprefix(path_to_walk).removeprefix("\\")
        for filename in filenames:
            ret.append(os.path.join(path,filename))

    return ret

class Environment:
    def __init__(self, printer, staging_dir, actions):
        self.printer = printer
        self.staging_dir = staging_dir
        self.actions = actions
        self.currentFiles = []

if __name__ == "__main__":

    # Setup arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s" , action='store_true', help="Stage")
    parser.add_argument("staging_files_dir" , help="Directory containing files to stage")
    args = parser.parse_args()
    
    if (args.s):
        stage_filename = os.path.join(args.staging_files_dir, STAGE_FILENAME)
    
        factory = ActionFactory()
        actionListLoaded = []
        with open(stage_filename, "r") as stageFile:
            lines = stageFile.readlines()
            for line in lines:
                if len(line) > 0:
                    newAction = factory.create(line)
                    if newAction != None:
                        actionListLoaded.append(newAction)
                    else:
                        print(CRED + "Invalid action: " + line + CEND)
        
        print ("====Loaded actions====")
        for action in actionListLoaded:
           print(action.serialize()) 

        print("====Staging====")
        printer = unity.USBConnection(pid=PRINTER_PID)
        env = Environment(printer, args.staging_files_dir, actionListLoaded)
        for action in actionListLoaded:
            action.validate(env)
    
        for action in actionListLoaded:
            action.execute(env)
    else:
        # Check if staging file already exists, prompt user to confim overwrite if it does
        stage_filename = os.path.join(args.staging_files_dir, STAGE_FILENAME)
        if os.path.isfile(stage_filename):
            confirm = input("Staging config file already exists. Overwrite? (y/n)")
            if confirm != "y":
                exit()
    
        actions = ActionFactory().createFromDir(args.staging_files_dir)
        
        print("====Generating staging config file====")
        with open(stage_filename, "w") as stageFile:
            for action in actions:
                print(action.serialize())
                stageFile.write(action.serialize() + '\n')


#TODO: 
#- Download Standard emulation files  
#- Detect channel firmware 
