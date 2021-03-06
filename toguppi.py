#!/datax/scratch/AMITY_INDIA/avi/github/casadev/bin/python3.8

from collections import defaultdict
from string import whitespace
import numpy as np
from pathlib import Path
from baseband import guppi
import sys
from os import path, system
import time
import argparse
import astropy.units as u
import warnings

def gmrt_guppi_bb(rawfile, npol=2, header=None, chunk=None, samples_per_frame=4096, nchan=1):
    """
    To read gmrt raw voltages file of GWB to convert to guppi raw

    :USAGE:
    --------
    $ gmrt_raw_toguppi [-h] [-f FILENAME] [-c CHUNK] [-hdr HEADER] [-hf HEADER_FILE] [-hfo HEADER_FILE_OUTPUT]

    To read gmrt raw voltages file of GWB to convert to guppi raw

    optional arguments:
    -h, --help            show this help message and exit
    -f FILENAME, --filename FILENAME
                        Input filename for conversion to guppiraw.
    -c CHUNK, --chunk CHUNK
                        Input chunk size to read the desired chunk of byte.
    -hdr HEADER, --header HEADER
                        Input header to inject to the raw file.
    -hf HEADER_FILE, --header-file HEADER_FILE
                        Input header from path to inject to the raw file.
    -hfo HEADER_FILE_OUTPUT, --header-file-output HEADER_FILE_OUTPUT
                        output header from path to inject to the raw file.
    
    NOTE
    ----- 
    imaginary data is not being read as documentation(https://baseband.readthedocs.io/en/stable/api/baseband.guppi.open.html#baseband.guppi.open):
    For GUPPI, complex data is only allowed when nchan > 1.
    """
    b=time.time()
    if path.isfile(rawfile):
        rawname=Path(rawfile).stem
        if header is None:
            header = {#'CHAN_BW':-100,
        'TBIN':1, #provide sample rate in astropy.units * Hz
        'TELESCOP':'GMRT',
        'NPOL':npol,
        'NCHAN':nchan,
        'OBSERVER':'Vishal Gajjar',
            'STT_IMJD':58132,
            'STT_SMJD':51093,
        'NBITS':8}
        print(f'selected parameters: rawfile={rawfile}, npol={npol}, header={header}, chunk={chunk}, samples_per_frame={samples_per_frame}, nchan={nchan}')
        print(f'copying file:{rawfile}')
        if chunk is None:
            npcm_data=np.memmap(rawfile, dtype='<i1', mode='r' )#,shape=(4096,))
        else:
            npcm_data=np.memmap(rawfile, dtype='<i1', mode='r', shape=(chunk,))
        print(f'copied file :{time.time()-b}')
        #npcm_data.flush()
        #number_of_frames = totalsamples/samples_per_frame
        #shape = (samples_per_frame,number_of_frames)
        #npcm_data.flush()
        
        real1_d =npcm_data # 0,2,4 indexed
        im_d=np.zeros(np.shape(real1_d))
        
        resd=np.array([real1_d,im_d], dtype='<i1').transpose()
        
        guppifile=rawname+''
        print(f'writing file stem: {guppifile}')
        #fgh = guppi.open(guppifile+'_guppi.{file_nr:04d}.raw', 'ws', frames_per_file=1180013,
        fgh = guppi.open(guppifile+'_guppi.0000.raw', 'ws',
                    samples_per_frame=samples_per_frame, nchan=nchan,
                    #npol=npol, #sample_rate=2.0E+08*u.Hz,
                    **header)
        print(f'data shape: {np.shape(resd)}')
        fgh.write(resd)


# -------------- when you have [p1r1,p1i1,p2r1,p2i1...]


        # im_d = npcm_data[1::2] # even indexed

        # ## pol1, pol2 = npcm_data[::2], npcm_data[1::2] # if no imaginary is in the bytes
        # #pol1, pol2 = real_d[::2], real_d[1::2]
        # ## pol1, pol2 = npcm_data[::2][::2], npcm_data[::2][1::2]
        
        # pol1_real = real_d[::2]
        # pol2_real = real_d[1::2]
        
        # pol1_im=im_d[1::2]
        # pol2_im=im_d[::2] # if you need imaginary and real
        # pol1=pol1_real+pol1_im*1j
        # pol2=pol2_real+pol2_im*1j
        
        
        # #resd=np.array([pol1,pol2]).transpose()
        # guppifile=rawname+''
        # print(f'writing file stem: {guppifile}')
        # #fgh = guppi.open(guppifile+'_guppi.{file_nr:04d}.raw', 'ws', frames_per_file=1180013,
        # fgh = guppi.open(guppifile+'_guppi.0000.raw', 'ws',
        #             samples_per_frame=samples_per_frame, nchan=nchan,
        #             #npol=npol, #sample_rate=2.0E+08*u.Hz,
        #             **header)
        # #fgh.write(resd)
        # resd=np.array([[pol1,pol2],[pol1,pol2]] , dtype='complex64').transpose()
        # print(f'data shape: {np.shape(resd)}')
        # #fgh.write(np.array([npcm_data[::2][::2], npcm_data[::2][1::2]]).transpose())
        # fgh.write(resd)
        #fgh.write(np.array(npcm_data))
        print(f'file writing completed: {time.time()-b}')
        fgh.close()
        return f'file created: {guppifile}'
    else:
        return f'file does not exist : {rawfile}'


def pasvraw(rawfile, nchan, chunk=None, chunk_n=1):
    """
    returns raw corrected FFT calculated value from PASV file,
    
    shape (numpy.ndarray)
    -----------------
    (nchan, totsamples_eachchan)
    
    params
    --------
    totsamples_eachchan = 2 * time samples (real, complex)
    nchan = 2048
    
    """
    
    dt = np.dtype([
        ('re', '<i1'), ('im','<i1') # 1 byte signed integer (little endian)
    ])
    if not chunk:
        chunk=path.getsize(rawfile)        
    if chunk%nchan !=0:
        extra_chunk=chunk%nchan
        warnings.warn(f'Ignoring last {extra_chunk} bytes!')
        chunk=chunk-extra_chunk
    # with open(rawfile, 'rb') as rw:
    #     rw_d=np.frombuffer(rw.read(chunk*chunk_n), dtype='<i4')
    if chunk:
        offchunk = int((chunk_n-1)*chunk)
        rw_d = np.memmap(rawfile, dtype='<i1', mode='r', shape=(chunk,), offset=offchunk ).copy()
        samplechfactored=nchan*2 # for real and imaginary
        totsamples_eachchan=int(chunk/samplechfactored)
        
        b=np.memmap('temp.b', dtype='<i1', mode='w+', shape=(totsamples_eachchan,nchan,2))
        print(f'running operation...1')
        b=np.hstack(rw_d.reshape(totsamples_eachchan,nchan,2))
        print(f'running operation...2')
        b=np.vstack([b,np.zeros(np.shape(b[0]))])
        print(f'running operation...3')
        b[nchan,:][::2]=b[0][1::2] # real of 2048 = im of 0
        print(f'running operation...4')
        #b=np.delete(b, 0, 0)
        b=b[1:(nchan+1), :]
        print(f'operations done...')
        return b , totsamples_eachchan
    else:
        warnings.warn(f'extra bytes:{extra_chunk} , chunk:{chunk}, channels:{nchan}')
        return 0,0

def header_from_file(hfile):
    with open(hfile) as hf:
        header = defaultdict(list)
        hfr=hf.read().splitlines()
        for i in range(len(hfr)):
            if '#' in hfr[i]:
                continue
            elif '=' in hfr[i]:
                hdrk,hdrv=hfr[i].split('=')
                try:
                    hdrv=int(hdrv)
                except:
                    try:
                        hdrv=float(hdrv)
                    except:
                        hdrv=str(hdrv).strip()
                #print(f'{hdrk}={hdrv}')#, type(hdrv))
                header[hdrk]=hdrv
                #header[hdrk]=hdrv
    return header



def wheader(header, filepath=None, padding=True):
    #p=[f"{k} = '{header[k]}'".ljust(80," ") for k in header if (header[k] and isinstance(header[k], str))]
    #p.extend(f"{k} = {header[k]}".ljust(80," ")  for k in header if (header[k] and not isinstance(header[k], str) or (header[k]==0)))
    p=[]
    for k in header: 
        if (header[k] and not isinstance(header[k], str) or (header[k]==0)):
            kad = f'{k}'.ljust(8," ")
            vad = f'{header[k]}'.rjust(21," ")
            p.append(f"{kad}= {vad}".ljust(80," "))
        if (header[k] and isinstance(header[k], str) or (header[k]=='')):
            vad = f'{k}'.ljust(8," ")
            kad = f'{header[k]}'.ljust(8," ")
            p.append(f"{vad}= '{kad}'".ljust(80," "))
    
    p.append(f'END'.ljust(80," "))
    whitespaces=''
    if header['DIRECTIO'] and padding:
        npad=0
        npad = 512-(len(p)*80)%512
        print(f'directio:1\n {len(p)*80}\n npad:{npad}')
        
        whitespaces=" "*npad
        #p.append(f'{whitespaces}')
    agg = ''
    
    for pr in p:
        agg+=pr
    agg+= whitespaces
    ##
    if filepath:
        with open(filepath, 'wb') as bf:
            bf.write(bytes(agg, encoding='ascii'))
    return agg, filepath


def payload(rawfile, nchan, hdr_p, out_guppi , chunk=None , blocksize=None, loop=False, chunk_n=1):
    """
    To read gmrt raw voltages file of GWB to convert to guppi raw

    :USAGE:
    --------
    $ gmrt_raw_toguppi [-h] [-f FILENAME] [-c CHUNK] [-hdr HEADER] [-hf HEADER_FILE] [-hfo HEADER_FILE_OUTPUT]

    To read gmrt raw voltages file of GWB to convert to guppi raw

    optional arguments:
    -h, --help            show this help message and exit
    -f FILENAME, --filename FILENAME
                        Input filename for conversion to guppiraw.
    -c CHUNK, --chunk CHUNK
                        Input chunk size to read the desired chunk of byte.
    -hdr HEADER, --header HEADER
                        Input header to inject to the raw file.
    -hf HEADER_FILE, --header-file HEADER_FILE
                        Input header from path to inject to the raw file.
    -hfo HEADER_FILE_OUTPUT, --header-file-output HEADER_FILE_OUTPUT
                        output header from path to inject to the raw file.
    """
    if blocksize is None:
        raise Exception(f'blocksize is not provided!')
    if not chunk:
        chunk=path.getsize(rawfile)        
    if chunk%nchan !=0:
        extra_chunk=chunk%nchan
        warnings.warn(f'Ignoring last {extra_chunk} of {chunk} bytes!')
        chunk=chunk-extra_chunk
    st_time = time.time()
    hdr,hfo=wheader(header_from_file(hdr_p))
    hdr_sz=len(hdr)
    print(f'reading from file......')
    bdata,totsamples_eachchan= pasvraw(rawfile, 2048, chunk, chunk_n)
    bdata=bdata.astype('<i1').ravel()
    if totsamples_eachchan:
        print(f'file copied : {np.round(time.time()-st_time, 2)}')
        totalsamplesize = chunk/nchan
        block_n=chunk/blocksize        
        print(f'header size: {hdr_sz}')
        frame_size = hdr_sz+blocksize
        totcolum = int(chunk/blocksize)
        final_size = frame_size*totcolum
        if path.isfile(out_guppi):
            system(f'rm -rf {out_guppi}')
        with open(out_guppi, 'ab') as cwb:
            sz=0
            i=0
            coleachframe=64
            complex_col_each_frame = coleachframe/2
            sampletime=81.92*10**(-6)
            obs_time = complex_col_each_frame*totcolum*sampletime
            print(f'total number of blocks: {totcolum}\n blocks in each frame:{coleachframe}\n final size: {final_size}\n observation time: {obs_time}')
            for i in range(totcolum): # writing each block
                start=int(i*coleachframe)
                end=(start+coleachframe)
                wrb=bytes(bdata[start:end])
                cwb.write(bytes(hdr, encoding='ascii'))
                cwb.write(wrb)
                sz += frame_size
                
            end_t = time.time() - st_time
            print(f'file created: {out_guppi}')
            print(f'completed: {np.round((sz/1048576),2)}MB \ttime elapsed:{np.round(end_t,2)}s')

parser = argparse.ArgumentParser('gmrt_raw_toguppi',description="""To read gmrt raw voltages file of GWB to convert to guppi raw
""", formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-f', '--filename',type=str,help="Input filename for conversion to guppiraw.", required=False)
parser.add_argument('-o', '--out_guppi',type=str,help="Output guppi guppi raw file.", required=False)
parser.add_argument('-c', '--chunk',type=int,help="Input chunk size to read the desired chunk of byte.", required=False)
#parser.add_argument('-hdr', '--header', type=str, help="Input header to inject to the raw file.", required=False)
headers=parser.add_argument_group('header', """Use the following arguments to create header from an input file to inject to the raw file. 
1) Input file should have headers in the following manner:
    BLOCSIZE=163840 | using # will comment the entire field.
2) use -hdr with -hf to update input file supplied field values.
    ex: gmrt_raw_toguppi -hf=headerinput.txt -hdr='TELESCOP=uGMRT,OBSERVER=John Doe'""")
headers.add_argument('-hdr','--header', type=str, help="Comma separated input headers to inject to the raw file.", required=False)
headers.add_argument('-hf', '--header-file', type=str, help="Input header from path to inject to the raw file.", required=False)
headers.add_argument('-hfo', '--header-file-output', type=str, help="Header output with the correct padding.", required=False)
headers.add_argument('-hio', '--header-direct-io', type=bool, help='If set to False bypasses padding for DIRECTIO=1 without affecting the header values. | Default: True')
args=parser.parse_args()

def cli():
    rawfile=args.filename
    chunk=args.chunk
    hlist=args.header_file
    hfo=args.header_file_output
    hdrin=args.header
    header = defaultdict(list)
    outguppi=args.out_guppi
    hio=args.header_direct_io
    if hio is None:
        hio=True
    # profiler = args.profiler

    if outguppi:
        outguppi_stem=Path(outguppi).stem
    # name handler
    if not outguppi and rawfile:
        outguppi=Path(rawfile).stem
        
    if hlist:
        header=header_from_file(hlist)
    if hdrin:
        hdrin=str(hdrin).strip()
        hdrdict=hdrin.split(',')
        for i in range(len(hdrdict)):
            if '=' in hdrdict[i]:
                hdrk,hdrv=hdrdict[i].split('=')
                try:
                    hdrv=int(hdrv)
                except:
                    try:
                        hdrv=float(hdrv)
                    except:
                        hdrv=str(hdrv).strip()
                header[hdrk]=hdrv  
    if hfo:
        printable_header, hfile_out=wheader(header,filepath=hfo, padding=hio)
        print(f'header file created: {hfile_out}')
    if rawfile:
        heavy_chunk=131072*3814#*1024 # 1 GB (in bytes)
        file_size=path.getsize(rawfile) # in bytes
        if file_size >= heavy_chunk:
            print(f'file size is heavy :{np.round(file_size/(1024*1024),2)}MB')
            extra_hchunk = file_size%heavy_chunk # extra heavy chunk
            nchunk = 2#int(file_size/heavy_chunk)
            echunk = (nchunk+1)
            for ic in range(1,echunk):
                print(f'nchunk:{ic}/{nchunk}')
                ret_payload = payload(rawfile, 2048, hlist, outguppi_stem + f'.000{ic-1}.raw' , chunk=heavy_chunk , blocksize=131072, loop=True, chunk_n=ic)
            if extra_hchunk:
                print(f'extra chunk: {extra_hchunk/(1024*1024)}MB')
                ret_payload = payload(rawfile, 2048, hlist, outguppi_stem + f'.000{echunk-1}.raw' , chunk=extra_hchunk , blocksize=131072, loop=True, chunk_n=echunk)
        else:
            if outguppi and not '.000' in outguppi:
                outguppi=outguppi + '.0000.raw'
            ret_payload = payload(rawfile, 2048, hlist, outguppi , chunk=None , blocksize=131072)
        print(ret_payload)

if __name__=='__main__':
    cli()