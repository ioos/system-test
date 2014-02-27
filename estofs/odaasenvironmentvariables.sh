# This file is named odaasenvironmentvariables.sh. It is the configuration file for ODAAS
##########################################################################################

# The top level dir for ODAAS
#export ODAASDIR=/odaas

# GLERL server used for glsea
export FtpGLERLserver=coastwatch.glerl.noaa.gov
export FTPGLERLsite=ftp.glerl.noaa.gov
#export MYSQLDIR=/usr/bin
# 20070306, ZB, After some work was done to odaas.ncd, ncl couldn't be found.
#export NCARG_ROOT=/usr/local
#export NCARG_ROOT=/odaas/oldfiles/test
#export PATH=$PATH:/usr/sbin:$NCARG_ROOT:$NCARG_ROOT/bin
export FtpNWSgateway=tgftp.nws.noaa.gov
export FtpGLERLserver=coastwatch.glerl.noaa.gov
export RFCFTPDIR=/var/ftp/pub/upload

# temp server var for testing
#export FtpTEMPserver=wx20jk@dew.ncep.noaa.gov

#######* NCEP SERVER VARIABLES
# 2006-01-12; ZB; Changed to using 4 vars that depend on which NCEP server is used: Mist, Dew, WOC, etc
#
### Vars for NCEP/EMC/MMAB polar ftp server
export FtpPOLARserver=polar.ncep.noaa.gov
#
## Vars for NCEP/Ocean Prediction Center
export FtpOPCserver=ftp.mpc.ncep.noaa.gov
#
### vars for WOC 
export protocol="ftp"
export ServerDirPrefix=/pub/data/nccf
export FtpIBMserver=ftpprd.ncep.noaa.gov
export ServerDirSuffix=HH
###
