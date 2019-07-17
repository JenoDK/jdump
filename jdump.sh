#!/bin/sh
my_dir=`dirname $0`
. $my_dir/config.cfg

configFile=$my_dir/config.cfg

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
LIGHT_BLUE='\033[1;34m'
NC='\033[0m'

function usage {
  echo -e "${LIGHT_BLUE}Usage: ./jdump.sh or alias [ -h | --help ] [ --config ] [ -sc | --show-config ] [ -cd | --create-dump ] [ -ld | --list-dumps ] [ -rd | --restore-dump ] [ -dd | --drop-db ]"
  echo -e "${GREEN} -h | --help                       ${CYAN}Show this"
  echo -e "${GREEN} -sc | --show-config               ${CYAN}Print the current configuration"
  echo -e "${GREEN} -cd | --create-dump               ${CYAN}Creates a dump, pass one argument for name prefix (f.e. -cd dump_for_demo), the current date will be added as well"
  echo -e "${GREEN} -ld | --list-dumps                ${CYAN}List the dumps from the dump directory, pass an argument to match */*argument*.sql"
  echo -e "${GREEN} -rd | --restore-dump              ${CYAN}Restores the dump specified in the argument, use the path displayed in -ld because we need the spaces (if present) escaped (f.e. -rs /Users/user/dumpFolder/dump.sql)"
  echo -e "${GREEN} -dd | --drop-db                   ${CYAN}Drop the current database (this includes emptying SESSION and GLOBAL sql modes)"
  echo -e "${GREEN} --config                          ${CYAN}Opens the config file"
                                                      #${CYAN}Sets the config located in config.cfg. Example: jdump --config=database:qiagen
}

function restoreDump {
  sqlDump="$1"

  echo -e ${LIGHT_BLUE}First dropping db
  dropDatabase
  echo -e ${LIGHT_BLUE}Starting restore of "$sqlDump"
  mysql -u $databaseUser -p$databasePassword $database < "$sqlDump"
  echo -e ${LIGHT_BLUE}Finished restore of "$sqlDump"
}

function listDumps {
  contains=$1
  echo -e ${CYAN}
  # Find dumps files matching '*'$contains'*.sql' and add escapes to spaces for the purpose of copy pasting
  find "$dumpFolder" -type f -name '*'$contains'*.sql' -print0 | xargs -0 ls -ltr | sed -e 's/ /\\ /g'
  echo -e ${NC}
}

function createDump {
  date=$(date '+%d-%b-%Y')
  sqlDump=$1'_'$date.sql
  echo -e ${LIGHT_BLUE}"Creating dump " $sqlDump " in folder $dumpFolder"
  echo -e ${CYAN}---mysql---
  mysqldump -u $databaseUser -p$databasePassword $database > "$dumpFolder/$sqlDump"
  echo -e ---mysql---${NC}
}

function config {
  #empty=""
  #config="${1/--config=/$empty}"
  #configKey="$(cut -d':' -f1 <<<"$config")"
  #configValue="$(cut -d':' -f2 <<<"$config")"
  #echo -e ${LIGHT_BLUE}Replacing $configKey with $configValue ${NC}
  #sed -i '' "/\(^$configKey=\).*/ s//\1$configValue/" $configFile

  open $configFile
}

function showConfig {
  echo -e ${LIGHT_BLUE}${configFile}${GREEN}
  cat ${configFile}
}

function dropDatabase {
  echo -e ${LIGHT_BLUE}Start dropping of $database DB
  echo -e ${CYAN}---mysql---
  mysqladmin -u $databaseUser -p$databasePassword drop $database
  mysqladmin -u $databaseUser -p$databasePassword create $database
  mysql -u genohm -pgenohm $database -e "SET SESSION sql_mode = '';"
  mysql -u genohm -pgenohm $database -e "SET GLOBAL sql_mode = '';"
  echo -e ---mysql---${NC}
  echo -e ${LIGHT_BLUE}Finished dropping of $database DB
}

while(($#)) ; do
    case $1 in
        -dd | --drop-db )       dropDatabase
                                exit
                                ;;
        -sc | --show-config )   showConfig
                                exit
                                ;;
        --config=* | --config ) config "$1"
                                exit
                                ;;
        -ld | --list-dumps )    listDumps "$2"
                                exit
                                ;;
        -cd | --create-dump )   createDump "$2"
                                exit
                                ;;
        -rd | --restore-dump )  restoreDump "$2"
                                exit
                                ;;
        -h | --help )           usage
                                exit
                                ;;
        *)                      echo -e ${RED}"Unknown option $1"
                                usage
                                exit
                                ;;
    esac
done
