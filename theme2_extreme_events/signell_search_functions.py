
def nearxy(x,y,xi,yi):
    """
    find the indices x[i] of arrays (x,y) closest to the points (xi,yi)
    """
    ind=ones(len(xi),dtype=int)
    dd=ones(len(xi),dtype='float')
    for i in arange(len(xi)):
        dist=sqrt((x-xi[i])**2+(y-yi[i])**2)
        ind[i]=dist.argmin()
        dd[i]=dist[ind[i]]
    return ind,dd


def find_ij(x,y,d,xi,yi):
    """
    find non-NaN cell d[j,i] that are closest to points (xi,yi).
    """
    index = where(~isnan(d.flatten()))[0]
    ind,dd = nearxy(x.flatten()[index],y.flatten()[index],xi,yi)
    j,i=ind2ij(x,index[ind])
    return i,j,dd


def find_timevar(cube):
    """
    return the time variable from Iris. This is a workaround for
    Iris having problems with FMRC aggregations, which produce two time coordinates
    """
    try:
        cube.coord(axis='T').rename('time')
    except:
        pass
    timevar = cube.coord('time')
    return timevar
    

def ind2ij(a,index):
    """
    returns a[j,i] for a.ravel()[index]
    """
    n,m = shape(lon)
    j = ceil(index/m).astype(int)
    i = remainder(index,m)
    return i,j