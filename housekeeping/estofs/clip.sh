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
#		Clips first NTIME timesteps from a ESTOFS field file (e.g. estofs.atl.t??z.fields.cwl.nc) #		  and creates a clipped ESTOFS file called OUTFILE
#
# Usage:  	Interactively:  clip.sh NTIME estofs.atl.t??z.fields.cwl.nc OUTFILE
#                           Example: clip.sh estofs.atl.t12z.fields.cwl.nc 6 $outfile
# Input Parameters:  estofs.sh infile NTIMES outfile
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
# Output Files:   (clipped file)
#
# Libraries Used:  "ncks" executable from NetCDF Operators (NCO): http://nco.sourceforge.net/
#
# Remarks:  NCO can be tough to build.  Try the binaries from http://nco.sourceforge.net/#Binaries
#           before building from source.   

# Obtain info on model cycle date/time via user entered arguments
# Check if sufficient number of arguments entered
if test $# != 3 
  then 
    echo ***Error: You must supply 3 arguments for input file name, number of time steps and output file!
    echo 'Example: clip.sh estofs.atl.t12z.fields.cwl.nc 6 outfile'
    exit
fi

# use NCO ncks program  to extract the first $2=ntime steps (with "Fortran" 1-based indexing)
# from dimension named "time" in $1=INFILE and store the output in $3=OUTFILE

/usr/local/bin/ncks -F -d time,$2 $1 $3

# end