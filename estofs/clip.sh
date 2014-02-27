#!/bin/sh
#
#---------------------------------------------------------------------------------------
#
# Program Name:  clip.sh
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
#		Clips first NTIME timesteps from a ESTOFS field file (e.g. estofs.atl.t??z.fields.cwl.nc) #		  and creates a clipped ESTOFS file with the same name in the directory OUTDIR
#
# Usage:  	Interactively:  clip.sh NTIME estofs.atl.t??z.fields.cwl.nc OUTDIR
#                           which creates a clipped version of estofs.atl.t??z.fields.cwl.nc in OUTDIR
#                           Example: clip.sh 6 estofs.atl.t12z.fields.cwl.nc ./agg_dir
#                                    clips first 6 time steps, creates file in ./agg_dir
# Input Parameters:  estofs.sh NTIME input_file OUTDIR
#
#
# Language:  Bourne Shell Script
#
# Target Computer:  NCEP WOC FTP SERVER 
#
# Script Execution Time: ?
#
# Programs Called:
#
# Input Files: estofs.atl.t??z.fields.cwl.nc (original file)
#
# Output Files: $OUTDIR/estofs.atl.t??z.fields.cwl.nc  (clipped file)
#
# Libraries Used:  "ncks" executable from NetCDF Operators (NCO): http://nco.sourceforge.net/
#
# Remarks:  NCO can be tough to build.  Try the binaries from http://nco.sourceforge.net/#Binaries
#           before building from source.   

# Obtain info on model cycle date/time via user entered arguments
# Check if sufficient number of arguments entered
if test $# != 3 
  then 
    echo ***Error: You must supply 3 arguments for file name, number of time steps and output dir!
    echo 'Example: clip.sh 6 estofs.atl.t12z.fields.cwl.nc ./agg_dir'
    exit
fi

# use NCO ncks program  to extract the first $2=ntime steps (with "Fortran" 1-based indexing)
# from dimension named "time" and store the output in $3=DIR/$1=FILE

/usr/local/bin/ncks -F -d time,$2 $1 $3/$1

# end