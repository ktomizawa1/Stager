from zebra.io import unity
import os
import argparse
import time
import logging
import sys
from datetime import timedelta
from Actions import *
from Utils import *

os.system("")

PRINTER_MODEL_PID = {
    "ZQ6RPlus" : 0x01D3,
    "ZQ6Plus" : 0x01D5,
    "ZQ6"     : 0x014E 
}

STAGE_FILENAME = "stage_config.txt"
LOGGING_FILENAME = "output.log"
OUTPUT_DIR = "__output"

class Environment:
    def __init__(self, printer, staging_dir, output_dir, actions):
        self.printer = printer
        self.staging_dir = staging_dir
        self.output_dir = output_dir
        self.actions = actions
        self.currentFiles = []

if __name__ == "__main__":
    # Setup arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s" , help="Stage printer. Provide printer model name")
    parser.add_argument("staging_files_dir" , help="Directory containing files to stage")
    args = parser.parse_args()

    output_dir = os.path.join(args.staging_files_dir, OUTPUT_DIR)
    stage_filepath = os.path.join(output_dir, STAGE_FILENAME)

    if (args.s):
        if (args.s not in PRINTER_MODEL_PID):
            print("ERROR: Invalid printer model")
            exit()
        
        start = time.time()
    
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(output_dir, LOGGING_FILENAME)),
                logging.StreamHandler(sys.stdout)
            ]
        )

        # Load all actions
        factory = ActionFactory()
        actionListLoaded = []
        with open(stage_filepath, "r") as stageFile:
            lines = stageFile.readlines()
            for line in lines:
                if len(line) > 0:
                    newAction = factory.create(line)
                    if newAction != None:
                        actionListLoaded.append(newAction)
                    else:
                        logging.warning(CRED + "Invalid action: " + line + CEND)
        
        logging.info ("====Loaded actions====")
        for action in actionListLoaded:
           logging.info(action.serialize()) 

        logging.info("====Staging====")
        PRINTER_PID = PRINTER_MODEL_PID[args.s]
        printer = unity.USBConnection(pid=PRINTER_PID)
        env = Environment(printer, args.staging_files_dir, output_dir, actionListLoaded)
        for action in actionListLoaded:
            action.validate(env)
    
        for action in actionListLoaded:
            action.execute(env)

        executionTime = time.time() - start
        logging.info("====Staging complete====")
        logging.info("Execution time: {}".format(timedelta(seconds=executionTime)))
    else:
        # Check if staging file already exists, prompt user to confim overwrite if it does
        if os.path.isfile(stage_filepath):
            confirm = input("Staging config file already exists. Overwrite? (y/n)")
            if confirm != "y":
                exit()
        else:
            os.makedirs(output_dir, exist_ok=True)
    
        actions = ActionFactory().createFromDir(args.staging_files_dir, OUTPUT_DIR)
        
        print("====Generating staging config file====")
        with open(stage_filepath, "w") as stageFile:
            for action in actions:
                print(action.serialize())
                stageFile.write(action.serialize() + '\n')
