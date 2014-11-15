#!/bin/sh
#
#---------------------------------------------------------------------------------------
#
# Program Name:  estofs.sh
#
# Location:      $HOME04YC/ftp/scripts/estofs
#
# Technical Contact:    Yi Chen                         Org:    NOS/CSDL
#                       Phone:  301-713-2809 x120       E-Mail: Yi.Chen@noaa.gov
# Author:               Yi Chen                         Date:   5/28/2013
# Original Author:      John G.W. Kelley                Date:   9/2010
#
# Revisions:
#       Date          Author       Reason
#       06/01/13      Y Chen       Created on app04 to download estofs model data
#
# Abstract:
#		Core script to download estofs 00z, 06z, 12z, and 18z cycle netCDF files.
#     		The files are retrieved from NCEP's operational directory.  
#		NCEP:  /pub/data/nccf/com/estofs/prod/estofs.YYYYMMDD/
#               1) estofs.atl.t??z.fields.cwl.nc  (382 MB/cycle)
#               2) estofs.atl.t??z.points.cwl.nc  (1.4 MB/cycle)
#               3) estofs.atl.t??z.points.htp.nc  (1.4 MB/cycle)
#               to thredds server (app04)
#		NOS:   .../data/estofs/....
#		
#
# Usage:  	Interactively:  estofs.sh YYYY MM DD HH
#		Via cron cronthredds, is called by scripts estofs_00z.sh, estofs_06z.sh,
#               estofs_12z.sh, and estofs_18z.sh
#
# Input Parameters:  estofs.sh YYYY MM DD HH
#                       where date and time information for requested model cycle are
#                             YYYY=year, MM=month (ex. 03), DD=day of month (ex. 05),
#                             HH=hour (UTC) (ex. 00,...,18)
#
# Language:  Bourne Shell Script
#
# Target Computer:  NCEP WOC FTP SERVER 
#
# Script Execution Time: ?
#
# Programs Called:
#
# Input Files:
#
# Output Files:
#
# where.ftp                 	- ftp code for acquiring ESTOFS Model status file from NCEP 
# where_$CC                 	- copy of ESTOFS Model status file originally from NCEP
#     
# Libraries Used:  None
#
# Error Conditions:
#
# Remarks:    Script calls odaasenvironmentvariables.sh to set global variables.
#
#-------------------------------------------------------------------------------------------

# Set environment variables, ftp address for NCEP IBM machine. ODAASDIR set in startup file,
# such as .bashrc, .profile
HOME04YC='/home/yi.chen.lx'
FTPDIR=$HOME04YC'/ftp'
. $FTPDIR/odaasenvironmentvariables.sh

# Obtain info on model cycle date/time via user entered arguments
# Check if sufficient number of arguments entered
if test $# != 4 
  then 
    echo ***Error: You must supply 4 arguments for model cycle date and time.
    echo 'Example: estofs.sh 2009 09 16 00'
    exit
fi
#

YYYY=$1
MM=$2
DD=$3
HH=$4
YYYYMMDD=$YYYY$MM$DD
echo 'estofs.sh' $YYYY $MM $DD $HH 'has started'

# -------------------- Set default directories --------------------------------------
DATADIR='/opt/thredds/data'
ESTOFSDATADIR=$DATADIR'/estofs'
ESTOFSDATAPOOLDIR=$DATADIR'/estofs/datapool'

SCRIPTSDIR=$FTPDIR'/scripts'
ESTOFSSCRIPTSDIR=$SCRIPTSDIR'/estofs'

LOGDIR=$FTPDIR'/execlog'
ESTOFSLOGDIR=$LOGDIR'/estofs'

#EXECDIR=$FTPDIR'/exec'
#SORCDIR=$FTPDIR'/sorc'

SHORTTERMESTOFSDIR=$ESTOFSDATADIR'/'$YYYY$MM$DD
CURRENTDIR=$ESTOFSDATADIR'/recent'
#
# (LONGTERMARCHIVES - if there is any)
#LONGTERMESTOFSARCHIVES=$ESTOFSDATADIR'/archives/'$YYYY$MM$DD
#
HOST='ftpprd.ncep.noaa.gov'
NCEPESTOFSDIR='/pub/data/nccf/com/estofs/prod/estofs.'$YYYY$MM$DD

# RPS
STAGE_DIR='/pub/data/nccf/com/estofs/stage_dir'
AGG_DIR='/pub/data/nccf/com/estofs/agg_dir'
echo 'stage_dir:'$STAGE_DIR
echo 'agg_dir:'$AGG_DIR
NTIME=6
#
echo '  ESTOFS script directory:' $ESTOFSSCRIPTSDIR
echo ' '
#
# Set log files
WHEREFTPLOG='whereftp.log'
ESTOFSFTPLOG='estofsftp.log'
FTPFILE='where.ftp'
#
# Time information for log files based on computer system clock 
time=`date -u +%T`
daywk=`date -u +%a`
today=`date -u +%Y%m%d`
HR=`date -u +%H`
MN=`date -u +%M`
# Obtain 2-digit year for use in degribbing section
YY=`echo $YYYY | awk '{ print substr($1, 3, 2)}'`
echo Two-digit year:  $YY
#
echo ' '
echo 'INFORMATION ON REQUESTED ESTOFS MODEL CYCLE'
echo '  date/time (Greenwich Day)'
echo '    year       :'  $YYYY
echo '    month      :'  $MM
echo '    day        :'  $DD
echo '    cycle (UTC):'  $HH
echo '    date       :'  $YYYYMMDD
echo ' '
#
# Set ESTOFS Model cycle
if [ $HH -eq "00" ]
 then
   CC=t00z
   CH=00
   CYCLE=0000
   MAXHR=1
elif [ $HH -eq "06" ]
 then
   CC=t06z
   CH=06
   CYCLE=0600
   MAXHR=7
elif [ $HH -eq "12" ]
 then
   CC=t12z
   CH=12
   CYCLE=1200
   MAXHR=13
elif [ $HH -eq "18" ]
 then
   CC=t18z
   CH=18
   CYCLE=1800
   MAXHR=19
else
 echo 'Cycle time must be 00, 06, 12, or 18 UTC.'
 exit
fi
#
# Set sleep parameters
SLEEPTIME=900
#
#
# Create year-month-day directory 
cd $ESTOFSSCRIPTSDIR
ESTOFSymddir=$ESTOFSDATADIR'/estofs.'$YYYY$MM$DD
echo 'ESTOFSymddir=' $ESTOFSymddir
mkdir -p $ESTOFSymddir $ESTOFSLOGDIR 
#
#
# Create directories
mkdir -p -m0777 $ESTOFSymddir
chmod 755 $ESTOFSymddir
#mkdir -p -m0777 $LONGTERMESTOFSARCHIVES/$YYYY$MM$DD/
#
#
# Set prefix file name for ESTOFS netcdf  
FILE1='estofs.atl.'$CC'.fields.cwl.nc'
FILE2='estofs.atl.'$CC'.points.cwl.nc'
FILE3='estofs.atl.'$CC'.points.htp.nc'
#RPS
FILE_AGG='estofs.atl.'$YYYY$MM$DD$HH'.fields.cwl.nc'
FILE_LATEST='estofs.atl.9999'$MM$DD$HH'.fields.cwl.nc'
#end RPS
#
# Use recent directory to temporally store ESTOFS model data
mkdir -p $CURRENTDIR
cd $CURRENTDIR
# download  file from NCEP
echo '  '
echo 'FTP to the NCEP computer...' $FtpIBMserver
echo '  using protocol:' $protocol  
#
#
# ------------------------------ FTP -------------------------------------------------
# SLEEP 15 minutes
#sleep $SLEEPTIME
#
# binary command doesn't work w/ sftp
#echo 'binary' > $SCRIPTDIR'/estofs_'$CC'.ftp'
rm $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
#echo anonymous >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
#echo yi.chen@noaa.gov >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
echo lcd $CURRENTDIR >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
echo cd $NCEPESTOFSDIR >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
#
#----- Obtain 6-hourly projections out to 24 hours 
echo 'get' $FILE1 >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
echo 'get' $FILE2 >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
echo 'get' $FILE3 >> $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
#
#
#
chmod 600 $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp'
#
echo 'Download output from NCEP computer...'
$protocol -v $FtpIBMserver < $ESTOFSSCRIPTSDIR'/estofs_'$CC'.ftp' > $ESTOFSLOGDIR/$ESTOFSFTPLOG
chmod 600 $ESTOFSLOGDIR/$ESTOFSFTPLOG
echo ' '
echo 'Finished ftping from NCEP computer...'
#
CURRENTDIRDOMAIN=$CURRENTDIR
cd $CURRENTDIRDOMAIN
ls -ltr
#
# ________________________________________________________
#
# RPS clipping for aggregation
# move file clipped at last cycle from stage directory to agg directory
mv $STAGE_DIR/*.nc $AGG_DIR
# remove full forecast from agg directory
rm $AGG_DIR/*9999*.nc
# place new full forecast in agg directory
cp $FILE1 $AGG_DIR/$FILE_LATEST
# call NCKS to clip 1st $NTIME steps out of file and put in stage directory
/usr/local/ncks -O -F -d time,1,$NTIME $FILE1 $STAGE_DIR/$FILE_AGG
# end RPS
echo ' Copy data to its destination directory and rename with date'
cp $FILE1 $ESTOFSymddir/$FILE1
cp $FILE2 $ESTOFSymddir/$FILE2
cp $FILE3 $ESTOFSymddir/$FILE3
echo Moved ESTOFS netcdf files to $ESTOFSymddir/$FILE1 
echo Moved ESTOFS netcdf files to $ESTOFSymddir/$FILE2 
echo Moved ESTOFS netcdf files to $ESTOFSymddir/$FILE3 
echo '________________________________________________________________'
echo ' '
#
#
echo ' Create soft links for each file to datapool'
cd $ESTOFSDATAPOOLDIR
ln -s $ESTOFSymddir/$FILE1 $YYYY$MM$DD.$FILE1
ln -s $ESTOFSymddir/$FILE2 $YYYY$MM$DD.$FILE2
ln -s $ESTOFSymddir/$FILE3 $YYYY$MM$DD.$FILE3
echo Create a symbolic link for $ESTOFSymddir/$FILE1 under $ESTOFSDATAPOOLDIR
echo Create a symbolic link for $ESTOFSymddir/$FILE2 under $ESTOFSDATAPOOLDIR
echo Create a symbolic link for $ESTOFSymddir/$FILE3 under $ESTOFSDATAPOOLDIR
echo '________________________________________________________________'
echo ' '
#


# Copy netCDF file into longterm archives directory
#echo 'Copy ESTOFS netCDF files into longterm archives directory: /opt/...../archives/....'
#echo $FILE1
#cp $ESTOFSymddir/$FILE1 $LONGTERMARCHIVES/$YYYY$MM$DD/$FILE1
#echo $FILE2
#cp $ESTOFSymddir/$FILE2 $LONGTERMARCHIVES/$YYYY$MM$DD/$FILE2
#echo $FILE3
#cp $ESTOFSymddir/$FILE3 $LONGTERMARCHIVES/$YYYY$MM$DD/$FILE3
#
#rm $FILE1 
#rm $FILE2 
#rm $FILE3 
#
#
echo ' '
echo `date`
echo '******** Finished estofs.sh script *********'
#
exit 
