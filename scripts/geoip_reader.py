import ipaddress

def varint(data,pos):
    n=0
    for shift in range(0,70,7):
        if pos>=len(data):raise ValueError('truncated varint')
        b=data[pos];pos+=1
        if shift==63 and b>1:raise ValueError('overflow varint')
        n|=(b&127)<<shift
        if b<128:return n,pos
    raise ValueError('invalid varint')
def fields(data):
    pos=0
    while pos<len(data):
        tag,pos=varint(data,pos);field,wire=tag>>3,tag&7
        if not field:raise ValueError('invalid field')
        if wire==0:value,pos=varint(data,pos)
        elif wire in (1,2,5):
            if wire==2:size,pos=varint(data,pos)
            else:size=8 if wire==1 else 4
            if pos+size>len(data):raise ValueError('truncated field')
            value=data[pos:pos+size];pos+=size
        else:raise ValueError('unsupported wire type')
        yield field,value

def read_geo(data):
    out={}
    for num,entry in fields(data):
        if num!=1:continue
        name=None;cidrs=[]
        for k,v in fields(entry):
            if k==1:name=v.decode().lower()
            elif k==3 and v:raise ValueError('inverse geoip unsupported')
            elif k==2:
                c=dict(fields(v));address=ipaddress.ip_address(c[1]);prefix=c.get(2,0)
                cidrs.append(ipaddress.ip_network((address,prefix),strict=True))
        if not name or name in out:raise ValueError('invalid or duplicate code')
        out[name]=cidrs
    return out
