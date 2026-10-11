import sys; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from gerb import *
from PIL import Image, ImageDraw, ImageFont
def grid(silkfile, maskfile, box, out, ppm=40, step=1.0):
    s=render(*parse_gerber(open(silkfile).read()),ppm=ppm)
    m=render(*parse_gerber(open(maskfile).read()),ppm=ppm)
    x0,x1,y0,y1=box
    W,H=s.size
    rgb=Image.new('RGB',s.size,(25,25,30))
    rgb.paste((150,120,50),mask=m)
    rgb.paste((240,240,240),mask=s)
    c=rgb.crop((int(x0*ppm),int((80-y1)*ppm),int(x1*ppm),int((80-y0)*ppm)))
    d=ImageDraw.Draw(c)
    f=ImageFont.load_default()
    import math
    xx=math.ceil(x0/step)*step
    while xx<=x1:
        X=(xx-x0)*ppm; maj=abs(xx-round(xx/5)*5)<1e-6
        d.line([(X,0),(X,c.size[1])],fill=(255,60,60) if maj else (90,40,40))
        if maj: d.text((X+2,2),str(int(xx)),fill=(255,90,90),font=f)
        xx+=step
    yy=math.ceil(y0/step)*step
    while yy<=y1:
        Y=(y1-yy)*ppm; maj=abs(yy-round(yy/5)*5)<1e-6
        d.line([(0,Y),(c.size[0],Y)],fill=(60,160,255) if maj else (30,60,100))
        if maj: d.text((2,Y+2),str(int(yy)),fill=(90,180,255),font=f)
        yy+=step
    c.save(out)
if __name__=='__main__':
    b=tuple(map(float,sys.argv[3:7])); grid(sys.argv[1],sys.argv[2],b,sys.argv[7],int(sys.argv[8]) if len(sys.argv)>8 else 40)
