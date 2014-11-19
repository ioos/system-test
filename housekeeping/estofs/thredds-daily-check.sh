#!/bin/sh
#
#---------------------------------------------------------------------------------------
#
# Program Name:  thredds-daily-check.sh
#
# Location:      $SCRIPTSDIR/daily-check
#
# Technical Contact:   	Yi Chen                         Org:  NOS/CSDL
#                      	Phone:  301-713-2809 x120    	E-Mail: yi.chen@noaa.gov
#
#
# Author:    Yi Chen  Date:  06/02/2013 
#
# Revisions:   
#           Date            Author                  Reason
#       Jun 02, 2013       Yi Chen       Created scripts to monitor and manage thredds data
# Abstract:
#            	Script displays disk quota of /opt; and delete data that is 32 days old
#
# Program Execution:  thredds-daily-check.sh
#
# Language:  Bourne Shell Script
#
# Script Execution Time: < 1 min
#
# Input Parameters:
#
# Language:  Bourne Shell Script
#
# Target Computer:  THREDDS server 
#
# Script Execution Time:  0100 UTC
#
# Programs Called:  dateformat datemath
#
# Input Files:  none
#
# Output Files:
#  Unit No.:  none
#  Name:  YYYYMMDD-THREDDS-daily-check.txt
#  Location:  $LOGDIR/status/
#  Description:  Text file that stores daily-check results
#
# Libraries Used:  None
#
# Error Conditions:
#
# Remarks:
#
#-------------------------------------------------------------------------------------------
#
# Call clone_terminator.sh to get rid of old jobs
$TOOLSDIR/terminators/clone_terminator.sh -p
$TOOLSDIR/terminators/clone_terminator.sh thredds-daily-check.sh
#
#-------------------- if use user entered arguments --------------------
# Obtain info on date/time via user entered arguments
#
# Check if sufficient number of arguments entered
#
#if test $# != 3
#  then
#    echo ***Error: You must supply 3 arguments for date.
#    echo 'Example: thredds-daily-check.sh 2010 01 02'
#    exit
#fi
#
#YYYY=$1
#MM=$2
#DD=$3
#-------------------- if use user entered arguments --------------------
#
# Obtain system time (or date and time) information (Greenwich Day)
#
YYYY=`date -u +%Y`
YY=`date -u +%y`
MM=`date -u +%m`
DD=`date -u +%d`
HR=`date -u +%H`
MN=`date -u +%M`
#
# Date and time settings
#
# --- Not working as for now -----
#currentYMD=`$TOOLSDIR/date/exec/dateformat $YYYY $MM $DD $HR $MN %Y%m%d`
currentYMD=`date +%Y%m%d`
#
#
# Info printing
#
echo "########################################################################################"
echo "#"
echo "#                      DAILY CHECK OF THREDDS DATA DIRECTORIES"
echo "#"
echo "#   Directories:   /opt/thredds/data/estofs  and  /opt/thredds/data/???????"
echo "#"
echo "#   Date:   $MM $DD $YYYY"
echo "#"
echo "#   Time:   $HR:$MN UTC"
echo "#"
echo "########################################################################################"
#
# Check and display disk storage
#
threddsusage=`df -hP /opt | awk '{printf "%s %s %s %s %s\n  ", $6, $2, $3, $4, $5}'`
#
echo "#"
echo "#   Disk Usage of /opt:"
echo "#"
echo "# $threddsusage"
echo "#"
echo "#"
#
#-------------------------------------------------------------------------------------------
# Check the date and delete data files that are more than 31 days old
#-------------------------------------------------------------------------------------------
#
daynow=`date '+%Y%m%d'`
daysago=32
let secondsago=$daysago*86400
let deletedate=`date '+%s'`-$secondsago
deleteOLDdate=`date -d @$deletedate '+%Y%m%d'`
#echo `date -d @$deletedate '+%Y%m%d'`
#
# Set directories
#
LOGDIR='/home/yi.chen.lx/ftp/execlog'
STATUSLOGDIR=$LOGDIR'/status'
#
DATADIR='/opt/thredds/data'
ESTOFSDATADIR=$DATADIR'/estofs'
ESTOFSDATAPOOLDIR=$DATADIR'/estofs/datapool'
deleteESTOFSdir=$ESTOFSDATADIR'/estofs.'$deleteOLDdate
ESTOFSdirToday=$ESTOFSDATADIR'/estofs.'$YYYY$MM$DD
#
estofsfiles='estofs.atl.t'??'z.'*.*'.nc'
fieldscwlfiles='estofs.atl.t'??'z.fields.cwl.nc'
pointshtpfiles='estofs.atl.t'??'z.points.htp.nc'
pointscwlfiles='estofs.atl.t'??'z.points.cwl.nc'
#
#
echo "ESTOFS Data Directory 31 days ago is:"
echo $deleteESTOFSdir
echo "files in OLD ESTOFS Data Directory are:"
echo `ls -l $deleteESTOFSdir/$estofsfiles`
echo "ESTOFS Data Directory Today is:"
echo $ESTOFSdirToday
echo "ls -l $estofsfiles"
echo `ls -l $ESTOFSdirToday/$estofsfiles`
#
echo "#"
echo ""
echo "########################################################################################"
echo "#"
echo "#               CHECK DATE & DELETE FILES THAT ARE MORE THAN 31 DAYS OLD"
echo "#"
echo "#   Current Date:"  $YYYY  $MM  $DD
echo "#"
echo "#   OLD Data Directory:"  $deleteESTOFSdir
echo "#"
echo "########################################################################################"
echo ""
#
#
if [ -d "$deleteESTOFSdir" ]; then
   echo "Old Estofs Data Directory exists"
   cd $deleteESTOFSdir
else
   echo "Old Estofs Data  Directory does NOT exist!"
   echo "Exit!"
   exit
fi
#
if [ "$(ls -A $deleteESTOFSdir/$estofsfiles)" ]; then
    echo "There is ESTOFS data exists in directory $deleteESTOFSdir"
    echo `ls -l $estofsfiles`
    echo "deleting estofs.atl.t??z.field.scwl.nc data ..."
    /bin/rm -f $deleteESTOFSdir/$fieldscwlfiles
    echo "Done."
    echo "deleting estofs.atl.t??z.points.htp.nc data ..."
    /bin/rm -f $deleteESTOFSdir/$pointshtpfiles
    echo "Done."
    echo "deleting estofs.atl.t??z.points.cwl.nc data ..."
    /bin/rm -f $deleteESTOFSdir/$pointscwlfiles
    if [ "$(ls -A $deleteESTOFSdir)" ]; then
        echo "CHECK! There are more files exist in $deleteESTOFSdir"
    else
        echo "EMPTY DIR, now removing old data directory $deleteESTOFSdir ..."
        /bin/rmdir "$deleteESTOFSdir"
    fi
    echo "Done."
#
else
    echo "NO ESTOFS data found in $deleteESTOFSdir"
fi
#
# ------ delete old soft links from datapool ------
#
cd $ESTOFSDATAPOOLDIR
echo `ls -l $deleteOLDdate.$estofsfiles`
echo "deleting $ESTOFSDATAPOOLDIR/$deleteOLDdate.$estofsfiles ..."
/bin/rm -f $ESTOFSDATAPOOLDIR/$deleteOLDdate.$estofsfiles
#
#
# ------ delete old status check log file as well ------
#
deleteLOGfile=$deleteOLDdate-THREDDS-daily-check.txt
#
cd $STATUSLOGDIR
if [ "$(ls -A $STATUSLOGDIR/$deleteLOGfile)" ]; then
    echo "Old status check log file exists"
    echo "deleting status check log $deleteLOGfile ..."
    /bin/rm -f $STATUSLOGDIR/$deleteLOGfile
    echo "Done."
fi
