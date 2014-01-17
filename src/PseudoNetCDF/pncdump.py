__doc__ = r"""
.. _dumper
:mod:`dumper` -- PseudoNetCDF dump module
============================================

.. module:: pncdump
   :platform: Unix, Windows
   :synopsis: Provides ncdump like functionaility for PseudoNetCDF
.. moduleauthor:: Barron Henderson <barronh@unc.edu>

"""

__all__=['pncdump',]
from numpy import float32, float64, int16, int32, int64, ndenumerate
from warnings import warn

import textwrap
import sys
import operator

def pncdump(f, name = 'unknown', header = False, variables = [], line_length = 80, full_indices = None, float_precision = 8, double_precision = 16, isgroup = False):
    """
    pncdump is designed to implement basic functionality
    of the NetCDF ncdump binary.
    
    f         - a PseudoNetCDFFile object
    name      - string name for the file 
                (equivalent to ncdump -n name)
    header    - boolean value for display of header only
                (equivalent to ncdump -h)
    variables - iterable of variable names for subsetting
                data display (equivalent to ncddump -v var[,...]

    pncdump(vertical_diffusivity('camx_kv.20000825.hgbpa_04km.TCEQuh1_eta.v43.tke',rows=65,cols=83))
    """
    file_type = str(type(f)).split("'")[1]
    formats = dict(float64 = "%%.%de" % (double_precision,), \
                   float32 = "%%.%de" % (float_precision,), \
                   int32 = "%i", \
                   int64 = "%i", \
                   str = "%s", \
                   bool = "%s", \
                   string8 = "'%s'")
    float_fmt = "%%.%df" % (float_precision,)
    int_fmt = "%i"
    # initialize indentation as 8 characters
    # based on ncdump
    indent = 8*" "
    if isgroup:
        startindent = 4*" "
    else:
        startindent = 4*""
        
    # First line of CDL
    if not isgroup: sys.stdout.write("%s %s {\n" % (file_type, name,))
    
    ###########################
    # CDL Section 1: dimensions
    ###########################
    sys.stdout.write(startindent + "dimensions:\n")
    for dim_name, dim in f.dimensions.iteritems():
        if dim.isunlimited():
            sys.stdout.write(startindent + 1*indent+("%s = UNLIMITED // (%s currently) \n" % (dim_name,len(dim))))
        else:
            sys.stdout.write(startindent + 1*indent+("%s = %s ;\n" % (dim_name,len(dim))))
    
    ###################################
    # CDL Section 2: variables metadata
    ###################################
    if len(f.variables.keys()) > 0:
        sys.stdout.write("\n" + startindent + "variables:\n")
    for var_name, var in f.variables.iteritems():
        var_type = dict(float32='float', \
                        float64='double', \
                        int32='integer', \
                        int64='long', \
                        bool='bool', \
                        string8='char', \
                        string80='char')[var.dtype.name]
        sys.stdout.write(startindent + 1*indent+("%s %s%s;\n" % (var_type, var_name,str(var.dimensions).replace('u\'', '').replace('\'','').replace(',)',')'))))
        for prop_name in var.ncattrs():
            prop = getattr(var, prop_name)
            sys.stdout.write(startindent + 2*indent+("%s:%s = %s ;\n" % (var_name,prop_name,repr(prop).replace("'", '"'))))
    
    ################################
    # CDL Section 3: global metadata
    ################################
    sys.stdout.write("\n\n// global properties:\n")
    for prop_name in f.ncattrs():
        prop = getattr(f, prop_name)
        sys.stdout.write(startindent + 2*indent+(":%s = %s ;\n" % (prop_name, repr(prop).replace("'",'"'))))

    if hasattr(f, 'groups'):
        for group_name, group in f.groups.iteritems():
            sys.stdout.write(startindent + 'group %s:\n' % group_name)
            pncdump(group, name = name, header = header, variables = variables, line_length = line_length, full_indices = full_indices, float_precision = float_precision, double_precision = double_precision, isgroup = True)
    if not header:
        # Error trapping prevents the user from getting an error
        # when they cancel a dump or when they break a redirected
        # pipe
        try:
            #####################
            # CDL Section 4: data
            #####################
            sys.stdout.write("\n\n" + startindent + "data:\n")
            
            # data indentation is only 1 space
            indent = " "
            
            # Subset variables for output
            display_variables = [var_name for var_name in f.variables.keys() if var_name in variables or variables == []]
            if variables != []:
                if len(variables) < len(display_variables):
                    warn("Not all specified variables were available")
            
            # For each variable outptu data 
            # currently assumes 3-D data
            for var_name in display_variables:
                var = f.variables[var_name]
                sys.stdout.write(startindent + 1*indent+("%s =\n" % var_name))
                if full_indices is not None:
                    id_display = {'f': lambda idx: str(tuple([idx[i]+1 for i in range(len(idx)-1,-1,-1)])), \
                                  'c': lambda idx: str(idx)}[full_indices]
                                  
                    for i, val in ndenumerate(var):
                        fmt = startindent + 2*indent+formats[var.dtype.name]
                        array_str = fmt % val
                        if i == tuple(map(lambda x_: x_ - 1, var.shape)):
                            array_str += ";"
                        else:
                            array_str += ","

                        array_str += " // %s%s \n" % (var_name, id_display(i))
                        try:
                            sys.stdout.write(array_str)
                        except IOError:
                            sys.stdout.close()
                            exit()
                else:
                    dimensions = [len(f.dimensions[d]) for d in var.dimensions]
                    if len(dimensions) > 1:
                        first_dim = reduce(operator.mul,dimensions[:-1])
                        second_dim = dimensions[-1]
                        shape = [first_dim, second_dim]
                    else:
                        shape = [1]+dimensions
                    var2d = var[...].reshape(shape)
                    fmt = ', '.join(shape[-1] * [formats[var.dtype.name]])
                    for rowi, row in enumerate(var2d):
                        try:
                            row = tuple(row)
                        except:
                            pass
                        array_str = fmt % row
                        if rowi == (shape[0]-1):
                            array_str += ';'
                        else:
                            array_str += ','
                            
                        try:
                            sys.stdout.write(textwrap.fill(array_str, line_length, initial_indent = startindent + '  ', subsequent_indent = startindent + '    '))
                            sys.stdout.write('\n')
                        except IOError, e:
                            warn(repr(e) + "; Typically from CTRL+C or exiting less")
                            exit()
                                            
                    
        except KeyboardInterrupt:
            sys.stdout.flush()
            exit()
    sys.stdout.write("}\n")

def main():
    from pncparse import pncparser
    ifile, ofile, options = pncparser(has_ofile = False)
    pncdump(ifile, header = options.header, full_indices = options.full_indices, line_length = options.line_length, float_precision = options.float_precision, name = options.cdlname)

if __name__ == '__main__':
    main()