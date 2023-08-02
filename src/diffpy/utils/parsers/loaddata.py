#!/usr/bin/env python
##############################################################################
#
# diffpy.utils      by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2010 The Trustees of Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Timur Davis, Chris Farrow, Pavol Juhas
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE_DANSE.txt for license information.
#
##############################################################################

import numpy


def loadData(filename, minrows=10, headers=False, hdel='=', hignore=None, **kwargs):
    """Find and load data from a text file.

    The data block is identified as the first matrix block of at least minrows rows
    and constant number of columns. This seems to work for most of the datafiles including
    those generated by PDFGetX2.

    filename    -- name of the file we want to load data from.
    minrows     -- minimum number of rows in the first data block.
                   All rows must have the same number of floating point values.
    headers     -- when False (defualt), the function returns a numpy array of the
                   data in the data block. When True, the function instead returns a
                   dictionary of parameters and their corresponding values parsed from
                   header (information prior the data block). See hdel and hignore for
                   options to help with parsing header information.
    hdel        -- (only used when headers enabled) delimiter for parsing header
                   information (default '='). e.g. using default hdel, the line
                   'parameter = p_value' is put into the dictionary as
                   {parameter: p_value}.
    hignore     -- (only used when headers enabled) ignore header rows beginning
                   with any elements in the hignore list. e.g. hignore=['# ', '[']
                   means the following lines are skipped: '# qmax=10', '[defaults]'.
    kwargs      -- keyword arguments that are passed to numpy.loadtxt including
                   the following arguments below. (See also numpy.loadtxt for more
                   details.)
    delimiter   -- delimiter for the data in the block (default use whitespace).
                   For comma-separated data blocks, set delimiter to ','.
    usecols     -- zero-based index of columns to be loaded, by default use
                   all detected columns. The reading skips data blocks that
                   do not have the usecols-specified columns.
    unpack      -- return data as a sequence of columns that allows tuple
                   unpacking such as  x, y = loadData(FILENAME, unpack=True).
                   Note transposing the loaded array as loadData(FILENAME).T
                   has the same effect.

    Return a numpy array of the data. If headers enabled, instead returns a
    dictionary of parameters read from the header.
    """
    from numpy import array, loadtxt
    # for storing header data
    hdata = {}
    # determine the arguments
    delimiter = kwargs.get('delimiter')
    usecols = kwargs.get('usecols')
    # required at least one column of floating point values
    mincv = (1, 1)
    # but if usecols is specified, require sufficient number of columns
    # where the used columns contain floats
    if usecols is not None:
        hiidx = max(-min(usecols), max(usecols) + 1)
        mincv = (hiidx, len(set(usecols)))
    # Check if a line consists of floats only and return their count
    # Return zero if some strings cannot be converted.
    def countcolumnsvalues(line):
        try:
            words = line.split(delimiter)
            # remove trailing blank columns
            while words and not words[-1].strip():
                words.pop(-1)
            nc = len(words)
            if usecols is not None:
                nv = len([float(words[i]) for i in usecols])
            else:
                nv = len([float(w) for w in words])
        except (IndexError, ValueError):
            nc = nv = 0
        return nc, nv
    # make sure fid gets cleaned up
    with open(filename, 'rb') as fid:
        # search for the start of datablock
        start = ncvblock = None
        fpos = (0, 0)
        nrows = 0
        for line in fid:
            # decode line
            dline = line.decode()
            # find header information if requested
            if headers:
                hpair = dline.split(hdel)
                flag = True
                # ensure number of non-blank arguments is two
                if len(hpair) != 2:
                    flag = False
                else:
                    # ignore if an argument is blank
                    hpair[0] = hpair[0].strip()  # name of data entry
                    hpair[1] = hpair[1].strip()  # value of entry
                    if not hpair[0] or not hpair[1]:
                        flag = False
                    else:
                        # check if row has an ignore tag
                        if hignore is not None:
                            for tag in hignore:
                                taglen = len(tag)
                                if len(hpair[0]) >= taglen and hpair[0][:taglen] == tag:
                                    flag = False
                # add header data
                if flag:
                    name = hpair[0]
                    value = hpair[1]
                    # check if data value should be stored as float
                    if isfloat(hpair[1]):
                        value = float(hpair[1])
                    hdata.update({name: value})
            # continue search for the start of datablock
            fpos = (fpos[1], fpos[1] + len(line))
            line = dline
            ncv = countcolumnsvalues(line)
            if ncv < mincv:
                start = None
                continue
            # ncv is acceptable here, require the same number of columns
            # throughout the datablock
            if start is None or ncv != ncvblock:
                ncvblock = ncv
                nrows = 0
                start = fpos[0]
            nrows += 1
            # block was found here!
            if nrows >= minrows:
                break

        # Return header data if requested
        if headers:
            return hdata  # Return, so do not proceed to reading datablock

        # Return an empty array when no data found.
        # loadtxt would otherwise raise an exception on loading from EOF.
        if start is None:
            rv = array([], dtype=float)
        else:
            fid.seek(start)
            # always use usecols argument so that loadtxt does not crash
            # in case of trailing delimiters.
            kwargs.setdefault('usecols', list(range(ncvblock[0])))
            rv = loadtxt(fid, **kwargs)
    return rv


class TextDataLoader(object):
    '''Smart loading of a text data with possibly multiple datasets.
    '''

    minrows = 10
    usecols = None
    skiprows = None

    def __init__(self, minrows=None, usecols=None, skiprows=None):
        if minrows is not None:
            self.minrows = minrows
        if usecols is not None:
            self.usecols = tuple(usecols)
        if skiprows is not None:
            self.skiprows = skiprows
        # data items
        self._reset()
        return


    def _reset(self):
        self.filename = ''
        self.headers = []
        self.datasets = []
        self._resetvars()
        return


    def _resetvars(self):
        self._filename = ''
        self._lines = None
        self._splitlines = None
        self._words = None
        self._linerecs = None
        self._wordrecs = None
        return


    def read(self, filename):
        with open(filename, 'rb') as fp:
            self.readfp(fp)
        return


    def readfp(self, fp, append=False):
        self._reset()
        # try to read lines from fp first
        self._lines = fp.readlines()
        # and if good, assign filename
        self.filename = getattr(fp, 'name', '')
        self._words = ''.join(self._lines).split()
        self._splitlines = [line.split() for line in self._lines]
        self._findDataBlocks()
        return


    def _findDataBlocks(self):
        mincols = 1
        if self.usecols is not None and len(self.usecols):
            mincols = max(mincols, max(self.usecols) + 1)
            mincols = max(mincols, abs(min(self.usecols)))
        nlines = len(self._lines)
        nwords = len(self._words)
        # idx - line index, nw0, nw1 - index of the first and last word,
        # nf - number of words, ok - has data
        self._linerecs = numpy.recarray((nlines,), dtype=[('idx', int),
            ('nw0', int), ('nw1', int), ('nf', int), ('ok', bool)])
        lr = self._linerecs
        lr.idx = numpy.arange(nlines)
        lr.nf = [len(sl) for sl in self._splitlines]
        lr.nw1 = lr.nf.cumsum()
        lr.nw0 = lr.nw1 - lr.nf
        lr.ok = True
        # word records
        lw = self._wordrecs = numpy.recarray((nwords,), dtype=[('idx', int),
            ('line', int), ('col', int), ('ok', bool), ('value', float)])
        lw.idx = numpy.arange(nwords)
        n1 = numpy.zeros(nwords, dtype=bool)
        n1[lr.nw1[:-1]] = True
        lw.line = n1.cumsum()
        lw.col = lw.idx - lr.nw0[lw.line]
        lw.ok = True
        values = nwords * [0.0]
        for i, w in enumerate(self._words):
            try:
                values[i] = float(w)
            except:
                lw.ok[i] = False
        # prune lines that have a non-float values:
        lw.values = values
        if self.usecols is None:
            badlines = lw.line[~lw.ok]
            lr.ok[badlines] = False
        else:
            for col in self.usecols:
                badlines = lw.line[(lw.col == col) & ~lw.ok]
                lr.ok[badlines] = False
        lr1 = lr[lr.nf >= mincols]
        okb = numpy.r_[lr1.ok[:1], lr1.ok[1:] & ~lr1.ok[:-1], False]
        oke = numpy.r_[False, ~lr1.ok[1:] & lr1.ok[:-1], lr1.ok[-1:]]
        blockb = numpy.r_[True, lr1.nf[1:] != lr1.nf[:-1], False]
        blocke = numpy.r_[False, blockb[1:-1], True]
        beg = numpy.nonzero(okb | blockb)[0]
        end = numpy.nonzero(oke | blocke)[0]
        rowcounts = end - beg
        assert not numpy.any(rowcounts < 0)
        goodrows = (rowcounts >= self.minrows)
        begend = numpy.transpose([beg, end - 1])[goodrows]
        hbeg = 0
        for dbeg, dend in begend:
            bb1 = lr1[dbeg]
            ee1 = lr1[dend]
            hend = bb1.idx
            header = ''.join(self._lines[hbeg:hend])
            hbeg = ee1.idx + 1
            if self.usecols is None:
                data = numpy.reshape(lw.value[bb1.nw0:ee1.nw1], (-1, bb1.nf))
            else:
                tdata = numpy.empty((len(self.usecols), dend - dbeg), dtype=float)
                for j, trow in zip(self.usecols, tdata):
                    j %= bb1.nf
                    trow[:] = lw.value[bb1.nw0 + j : ee1.nw1 : bb1.nf]
                data = tdata.transpose()
            self.headers.append(header)
            self.datasets.append(data)
        # finish reading to a last header and empty dataset
        if hbeg < len(self._lines):
            header = ''.join(self._lines[hbeg:])
            data = numpy.empty(0, dtype=float)
            self.headers.append(header)
            self.datasets.append(data)
        return


# End of class TextDataLoader

def isfloat(s):
    '''True if s is convertible to float.
    '''
    try:
        float(s)
        return True
    except:
        pass
    return False

# End of file