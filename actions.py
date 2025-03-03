import datetime
import os
import shutil
import sys
from datetime import date
from enum import Enum

import yaml
from functional import seq
from PyInquirer import Separator, prompt

import constants
from constants import BColors


class Config:
    def __init__(self, config_id, database, dumpFolder, databaseUser, databasePassword, databaseType='mysql', isDocker=False, dockerContainerName=None, dockerPort=None):
        self.config_id = config_id
        self.database = database
        self.dumpFolder = dumpFolder
        self.databaseUser = databaseUser
        self.databasePassword = databasePassword
        self.databaseType = databaseType
        self.isDocker = isDocker
        self.dockerContainerName = dockerContainerName
        self.dockerPort = dockerPort

class ChoiceGroups(Enum):

    DATABASE_ACTIONS = 'Database actions'
    CONFIG_ACTIONS = 'Configuration actions'
    OTHER = 'Other'

    def __init__(self, title):
        self.title = title

class Choices(Enum):

    RESTORE_DUMP = ChoiceGroups.DATABASE_ACTIONS, lambda config: 'Restore a dump', lambda config: restoreDump(config)
    CREATE_DUMP = ChoiceGroups.DATABASE_ACTIONS, lambda config: 'Create a dump from ' + config.database, lambda config: createDump(config)
    CLEAN_DB = ChoiceGroups.DATABASE_ACTIONS, lambda config: 'Make ' + config.database + ' empty.', lambda config: cleanDatabase(config)
    LIST_DUMPS = ChoiceGroups.DATABASE_ACTIONS, lambda config: 'List all dumps in ' + config.dumpFolder, lambda config: listDumps(config)
    INIT_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Initialize the configuration file', lambda config: initConfig()
    CHANGE_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Change the current configuration', lambda config: changeConfig()
    SHOW_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Show all configurations', lambda config: showAllConfig()
    SHOW_CURRENT_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Show current configuration', lambda config: showConfig(config)
    ADD_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Add a configuration', lambda config: addConfig()
    EDIT_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Edit a configuration', lambda config: editConfig()
    REMOVE_CONFIG = ChoiceGroups.CONFIG_ACTIONS, lambda config: 'Remove a configuration', lambda config: removeConfig(config)
    EXIT = ChoiceGroups.OTHER, lambda config: 'Exit', lambda config: exit()

    def __init__(self, group, title, function):
        self.group = group
        self.title = title
        self.function = function

    @staticmethod
    def objects(config):
        grouped_choices = seq(Choices) \
            .group_by(lambda c: c.group)
        questions = []
        for choiceGroup in list(ChoiceGroups):
            group = grouped_choices.find(lambda x: x[0] == choiceGroup)
            group_questions = seq(group[1]) \
                .map(lambda c: {
                    'name': c.title(config),
                    'value': c
                })
            questions.append(Separator('-' * 7 + ' ' + group[0].title + ' ' + '-' * 7))
            questions.extend(group_questions)
            questions.append(Separator(' '))
        return questions

def logError(msg):
    print(BColors.RED + 'ERROR: ' + msg + BColors.NC)

def getConfigFilePath():
    current_dir = os.path.dirname(sys.argv[0])
    return os.path.join(current_dir, 'config.yml')

def loadConfig():
    config_file_path = getConfigFilePath()
    if not os.path.exists(config_file_path):
        initConfig()
    with open(getConfigFilePath(), 'r') as stream:
        try:
            configs=yaml.safe_load(stream)
            configToUse=configs.get(constants.configToUseVarName)
            return extractConfigToUse(configToUse, configs)
        except yaml.YAMLError as exc:
            logError(str(exc))

def extractConfigToUse(configToUse, configs):
    if configToUse is None:
        logError('Config to use is not set in configuration')
        changeConfig()
        return loadConfig()
    if configToUse not in configs:
        logError('Could not find config ' + str(configToUse) + ' in configurations: ' + str(seq(configs.keys()).filter(lambda key: key != constants.configToUseVarName)))
        changeConfig()
        return loadConfig()
    return Config(
        configToUse,
        configs[configToUse]['database'], 
        configs[configToUse]['dumpFolder'], 
        configs[configToUse]['databaseUser'], 
        configs[configToUse]['databasePassword'],
        configs[configToUse].get('databaseType', 'mysql'),
        configs[configToUse].get('isDocker', False),
        configs[configToUse].get('dockerContainerName', None),
        configs[configToUse].get('dockerPort', None)
    )

def showMenu(config):
    print('Current configuration: ' + BColors.RED + str(config.config_id) + BColors.NC)
    questions = {
        'type': 'list',
        'name': 'choice',
        'message': 'What do you want to do?',
        'choices': Choices.objects(config)
    }
    answers = prompt(questions, style=constants.style)
    if bool(answers):
        return answers['choice']

def getDumps(config):
    def getCreatedDate(config, file):
        created_date_float = os.path.getctime(os.path.join(config.dumpFolder, file))
        created_date = datetime.datetime.fromtimestamp(created_date_float).strftime("%m/%d/%Y, %H:%M:%S")
        return created_date
    return seq(os.listdir(config.dumpFolder)) \
        .filter(lambda file: file.endswith(".sql")) \
        .order_by(lambda file: os.path.getctime(os.path.join(config.dumpFolder, file))) \
        .map(lambda file: (file, getCreatedDate(config, file))) \
        .to_dict()

def listDumps(config):
    for dump, created_date in getDumps(config).items():
        print(created_date + ' ' + dump)

def showAllConfig():
    with open(getConfigFilePath(), 'r') as stream:
        configs = yaml.safe_load(stream)
        all_configs = seq(configs.keys()).filter(lambda key: key != constants.configToUseVarName).map(lambda key: (key, extractConfigToUse(key, configs))).to_dict()
        for key, config in all_configs.items():
            print(BColors.LIGHT_BLUE + 'Configuration: ' + str(key))
            print(BColors.CYAN + 'database:' + str(config.database))
            print(BColors.CYAN + 'dumpFolder:' + str(config.dumpFolder))
            print(BColors.CYAN + 'databaseUser:' + str(config.databaseUser))
            print(BColors.CYAN + 'databasePassword:' + str(config.databasePassword) + BColors.NC)
            print(BColors.CYAN + 'databaseType:' + str(config.databaseType) + BColors.NC)
            print(BColors.CYAN + 'isDocker:' + str(config.isDocker) + BColors.NC)
            if config.isDocker:
                print(BColors.CYAN + 'dockerPort:' + str(config.dockerPort) + BColors.NC)
                print(BColors.CYAN + 'dockerContainerName:' + str(config.dockerContainerName) + BColors.NC)
            print()

def showConfig(config):
    print()
    print(BColors.LIGHT_BLUE + 'Using configuration:')
    print(BColors.CYAN + '- database:' + str(config.database))
    print(BColors.CYAN + '- dumpFolder:' + str(config.dumpFolder))
    print(BColors.CYAN + '- databaseUser:' + str(config.databaseUser))
    print(BColors.CYAN + '- databasePassword:' + str(config.databasePassword) + BColors.NC)
    print(BColors.CYAN + '- databaseType:' + str(config.databaseType) + BColors.NC)
    print(BColors.CYAN + '- isDocker:' + str(config.isDocker) + BColors.NC)
    if config.isDocker:
        print(BColors.CYAN + '- dockerPort:' + str(config.dockerPort) + BColors.NC)
        print(BColors.CYAN + '- dockerContainerName:' + str(config.dockerContainerName) + BColors.NC)

def restoreDump(config):
    dumps_dict = getDumps(config)
    dumps_choices = seq(dumps_dict.keys()) \
        .map(lambda key: {
            'name': dumps_dict[key] + ' ' + key,
            'value': key
        })
    if dumps_choices:
        questions = {
            'type': 'list',
            'name': 'dump',
            'message': 'What dump would you like to restore?',
            'choices': dumps_choices
        }
        answers = prompt(questions, style=constants.style)
        # Keyboard interrupt -> answers is empty
        if bool(answers):
            print('Cleaning the current database...')
            cleanDatabase(config)
            dump_to_restore = os.path.join(config.dumpFolder, answers['dump'])
            print('This can take a while depending on the size of the dump...')
            # docker exec -i mysql_slims_66 sh -c 'exec mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" slimsdb66 ' < /Users/dekeyzer/Documents/DbDumps/SLIMS/6.6/slims65_start.sql
            if config.databaseType == 'mysql':
                if config.isDocker:
                    os.system("docker exec -i %s sh -c 'exec mysql -uroot -p\\\"$MYSQL_ROOT_PASSWORD\\\" %s ' < %s" % (config.dockerContainerName, config.database, dump_to_restore))
                else:
                    os.system("mysql -u %s -p%s %s < %s" % (config.databaseUser, config.databasePassword, config.database, dump_to_restore))
            elif config.databaseType == 'postgres':
                if config.isDocker:
                    os.system("docker exec -i %s sh -c 'export PGPASSWORD=\"$POSTGRES_PASSWORD\" && psql -U %s -d %s' < %s" % (config.dockerContainerName, config.databaseUser, config.database, dump_to_restore))
                else:
                    os.environ["PGPASSWORD"] = config.databasePassword
                    os.system("psql -U %s -d %s < %s" % (config.databaseUser, config.database, dump_to_restore))
                    os.environ.pop("PGPASSWORD", None)
    else:
        logError("No dumps found in '%s'" % config.dumpFolder)
    

def createDump(config):
    now = date.today().strftime("%b-%d-%Y")
    questions = {
        'type': 'input',
        'name': 'dump_name',
        'message': "Name of the dump (will automatically be affixed by the current date and extension '_%s.sql')" % (now)
    }
    answers = prompt(questions, style=constants.style)
    if bool(answers):
        dump_location = config.dumpFolder + '/' + answers['dump_name'] + '_' + now + '.sql'
        if config.databaseType == 'mysql':
            if config.isDocker:
                os.system("docker exec %s sh -c 'exec mysqldump -uroot -p\\\"$MYSQL_ROOT_PASSWORD\\\" %s' > %s" % (config.dockerContainerName, config.database, dump_location))
            else:
                os.system("mysqldump -u %s -p%s %s > %s" % (config.databaseUser, config.databasePassword, config.database, dump_location))
        elif config.databaseType == 'postgres':
            if config.isDocker:
                os.system("docker exec %s sh -c 'export PGPASSWORD=\"$POSTGRES_PASSWORD\" && pg_dump -U %s -d %s' > %s" % (config.dockerContainerName, config.databaseUser, config.database, dump_location))
            else:
                os.environ["PGPASSWORD"] = config.databasePassword
                os.system("pg_dump -U %s -d %s > %s" % (config.databaseUser, config.database, dump_location))
                os.environ.pop("PGPASSWORD", None)

def cleanDatabase(config):
    questions = {
        'type': 'confirm',
        'message': 'Are you sure you want to drop the ' + config.database,
        'name': 'continue',
    }
    answers = prompt(questions, style=constants.style)
    if not answers['continue']:
        return
        
    if config.databaseType == 'mysql':
        if config.isDocker:
            os.system("docker exec %s sh -c 'exec mysqladmin -uroot -p\\\"$MYSQL_ROOT_PASSWORD\\\" -f drop %s'" % (config.dockerContainerName, config.database))
            os.system("docker exec %s sh -c 'exec mysqladmin -uroot -p\\\"$MYSQL_ROOT_PASSWORD\\\" create %s'" % (config.dockerContainerName, config.database))
        else:
            os.system("mysqladmin -u %s -p%s drop %s" % (config.databaseUser, config.databasePassword, config.database))
            os.system("mysqladmin -u %s -p%s create %s" % (config.databaseUser, config.databasePassword, config.database))
    elif config.databaseType == 'postgres':
        if config.isDocker:
            os.system("docker exec %s sh -c 'export PGPASSWORD=\"$POSTGRES_PASSWORD\" && dropdb -U %s --if-exists %s && createdb -U %s %s'" % 
                    (config.dockerContainerName, config.databaseUser, config.database, config.databaseUser, config.database))
        else:
            os.environ["PGPASSWORD"] = config.databasePassword
            os.system("dropdb -U %s --if-exists %s" % (config.databaseUser, config.database))
            os.system("createdb -U %s %s" % (config.databaseUser, config.database))
            os.environ.pop("PGPASSWORD", None)

def askWhichConfiguration(configs, question):

    def getChoiceObject(key, currentConfig):
        if key == currentConfig:
            name = str(key) + ' (current configuration)'
        else:
            name = str(key)
        return {
            'name': name,
            'value': key
        }

    configurations = seq(configs.keys()).filter(lambda key: key != constants.configToUseVarName).map(lambda key: getChoiceObject(key, configs.get(constants.configToUseVarName)))
    if not configurations:
        logError("No configurations found, please add one")
        addConfig()
        return None
    questions = {
        'type': 'list',
        'name': 'configuration',
        'message': question,
        'choices': configurations
    }
    return prompt(questions, style=constants.style)

def changeConfig():
    config_file = getConfigFilePath()

    with open(config_file, 'r') as stream:
        configs = yaml.safe_load(stream)
        answers = askWhichConfiguration(configs, 'What configuration do you want to use?')

        if bool(answers):
            configs[constants.configToUseVarName] = answers['configuration']
            
            with open(config_file, 'w') as f:
                yaml.dump(configs, f)
        else:
            exit()

def removeConfig(config):
    config_file = getConfigFilePath()

    with open(config_file, 'r') as stream:
        configs = yaml.safe_load(stream)
        answers = askWhichConfiguration(configs, 'What configuration do you want to remove?')

        if bool(answers):
            del configs[answers['configuration']]
            
            with open(config_file, 'w') as f:
                yaml.dump(configs, f)

def editConfig():
    config_file = getConfigFilePath()

    with open(config_file, 'r') as stream:
        configs = yaml.safe_load(stream)
        answers = askWhichConfiguration(configs, 'What configuration do you want to edit?')

        if bool(answers):
            chosen_config = answers['configuration']
            config_object = extractConfigToUse(chosen_config, configs)
            questions = [
                {
                    'type': 'input',
                    'name': 'config_key',
                    'message': 'Configuration key:',
                    'default': chosen_config
                },
                {
                    'type': 'input',
                    'name': 'database',
                    'message': 'Database:',
                    'default': config_object.database
                },
                {
                    'type': 'list',
                    'name': 'database_type',
                    'message': 'Database type:',
                    'choices': ['mysql', 'postgres'],
                    'default': config_object.databaseType
                },
                {
                    'type': 'input',
                    'name': 'dump_folder',
                    'message': 'Dump folder:',
                    'default': config_object.dumpFolder,
                    'validate': lambda val: os.path.isdir(val) or 'Directory does not exist'
                },
                {
                    'type': 'input',
                    'name': 'database_user',
                    'message': 'Database user:',
                    'default': config_object.databaseUser
                },
                {
                    'type': 'input',
                    'name': 'database_password',
                    'message': 'Database password:',
                    'default': config_object.databasePassword
                },
                {
                    'type': 'confirm',
                    'message': 'Is this a docker configuration',
                    'name': 'isDocker',
                    'default': config_object.isDocker,
                },
                {
                    'type': 'input',
                    'message': 'What is the docker container\'s name?',
                    'name': 'dockerContainerName',
                    'default': config_object.dockerContainerName,
                    'when': lambda answers: answers['isDocker']
                },
                {
                    'type': 'input',
                    'message': 'On what port is the docker container running?',
                    'name': 'dockerPort',
                    'default': config_object.dockerPort,
                    'when': lambda answers: answers['isDocker']
                }
            ]   
            edited_config = prompt(questions, style=constants.style)
            if bool(edited_config):
                new_config = {
                    'database': edited_config['database'],
                    'databasePassword': edited_config['database_password'],
                    'databaseUser': edited_config['database_user'],
                    'dumpFolder': edited_config['dump_folder'],
                    'databaseType': edited_config['database_type'],
                    'isDocker': edited_config['isDocker'],
                    'dockerContainerName': edited_config['dockerContainerName'],
                    'dockerPort': edited_config['dockerPort']
                }
                configs[chosen_config] = new_config

                with open(config_file, 'w') as f:
                    yaml.dump(configs, f)

def addConfig():
    config_file = getConfigFilePath()
    questions = [
        {
            'type': 'input',
            'name': 'config_key',
            'message': 'Configuration key:',
        },
        {
            'type': 'input',
            'name': 'database',
            'message': 'Database:',
        },
        {
            'type': 'list',
            'name': 'database_type',
            'message': 'Database type:',
            'choices': ['mysql', 'postgres']
        },
        {
            'type': 'input',
            'name': 'dump_folder',
            'message': 'Dump folder:',
            'validate': lambda val: os.path.isdir(val) or 'Directory does not exist'
        },
        {
            'type': 'input',
            'name': 'database_user',
            'message': 'Database user:'
        },
        {
            'type': 'input',
            'name': 'database_password',
            'message': 'Database password:'
        },
        {
            'type': 'confirm',
            'message': 'Is this a docker configuration',
            'name': 'isDocker',
            'default': False,
        },
        {
            'type': 'input',
            'message': 'What is the docker container\'s name?',
            'name': 'dockerContainerName',
            'when': lambda answers: answers['isDocker']
        },
        {
            'type': 'input',
            'message': 'On what port is the docker container running?',
            'name': 'dockerPort',
            'when': lambda answers: answers['isDocker']
        }
    ]
    answers = prompt(questions, style=constants.style)
    if bool(answers):
        with open(config_file, 'r') as stream:
            configs = yaml.safe_load(stream)
            new_config = {
                'database': answers['database'],
                'databasePassword': answers['database_password'],
                'databaseUser': answers['database_user'],
                'dumpFolder': answers['dump_folder'],
                'databaseType': answers['database_type'],
                'isDocker': answers['isDocker'],
                'dockerContainerName': answers.get('dockerContainerName'),
                'dockerPort': answers.get('dockerPort')
            }
            configs[answers['config_key']] = new_config

            with open(config_file, 'w') as f:
                yaml.dump(configs, f)
    else:
        exit()

def initConfig():
    current_dir = os.path.dirname(sys.argv[0])
    config_file = os.path.join(current_dir, 'config.yml')

    if os.path.exists(config_file):
        questions = {
            'type': 'confirm',
            'message': 'WARNING: This will overwrite your configuration file which is not empty. Do you want to continue?',
            'name': 'continue',
            'default': False
        }
        answers = prompt(questions, style=constants.style)
        if not answers['continue']:
            return

    new_config_file = open(config_file, "w")
    new_config_file.write(constants.configToUseVarName + ': ')