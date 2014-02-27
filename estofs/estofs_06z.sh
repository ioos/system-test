#!/bin/sh
#
#---------------------------------------------------------------------------------------
#
# Program Name:  estofs_06z.sh
#
# Location:      $HOME04YC/ftp/scripts/estofs
#
# Technical Contact:    Yi Chen                         Org:    NOS/CSDL
#                       Phone:  301-713-2809 x120       E-Mail: Yi.Chen@noaa.gov
# Author:               Yi Chen                         Date:   5/28/2013
# Original Author:      Jay Benedetti                   Date:   5/1/2009
#                       John G.W. Kelley
#
# Revisions:
#       Date          Author       Reason
#       06/01/13      Y Chen       Created on app04 for getting estofs_06z model run
#
# Abstract:
#       Script run from cron to set date parameters and launch estofs-scp.sh (core ESTOFS
#       retrieval script)
#
# Program Execution:  estofs_06z.sh
#
# Input Parameters:
#
# Language:  Bourne Shell Script
#
#
# Script Execution Time: < 1 min 
#
#
#-------------------------------------------------------------------------------------------
#
# Set environment variables, ftp address for NCEP IBM machine. $FTPDIR set in cronthredds
. $FTPDIR/odaasenvironmentvariables.sh
# Call clone_terminator.sh to get rid of old jobs
$TOOLSDIR/clone_terminator.sh -p
$TOOLSDIR/terminators/clone_terminator.sh estofs_06z.sh

# Obtain system date/time information (Greenwich Day)
YYYY=`date -u +%Y`
YY=`date -u +%y`
MM=`date -u +%m`
DD=`date -u +%d`
HR=`date -u +%H`
MN=`date -u +%M`
time=`date -u +%T`
JD=`date -u +%j`
#
# Set ESTOFS Model cycle
HH=06
#
echo 'System clock date/time (Greenwich Day)'
echo 'system clock year  :'  $YYYY
echo 'system clock month :'  $MM
echo 'system clock day   :'  $DD
echo 'system clock hour  :'  $HR
echo 'system clock minute:'  $MN
echo 'cycle time	 :'  $HH
#
# Set sleep parameters and SLEEP 15 minutes
SLEEPTIME=900
sleep $SLEEPTIME
#
#
# Call core ESTOFS program estofs.sh
echo 'Script called:  estofs.sh' $YYYY $MM $DD $JD $HH
$SCRIPTSDIR/estofs/estofs.sh $YYYY $MM $DD $HH
