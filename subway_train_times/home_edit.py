"""Home Edit: shared-home 800x480 e-ink layout, with no live clock or transit.

Pure rendering functions accept injected data for offline tests. Fonts and art
are bundled; rendering does not depend on a CDN or image-generation service.
"""
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SCALE = 2
REGIONS = {'sidebar':(415,78,774,343), 'banner':(26,365,774,472),
           'fullscreen':(26,78,774,472)}

@lru_cache(maxsize=48)
def font(size, face='sans', scale=SCALE):
    name = 'InstrumentSerif-Regular.ttf' if face == 'serif' else 'DMSans.ttf'
    return ImageFont.truetype(str(ROOT / 'fonts' / name), int(size*scale))


def _text(d,x,y,value,size=20,face='sans',anchor=None,max_width=None):
    value=str(value)
    if max_width is not None:
        while size>12 and d.textbbox((0,0),value,font=font(size,face))[2]>max_width*SCALE:
            size-=1
    d.text((int(x*SCALE),int(y*SCALE)),value,font=font(size,face),fill=0,anchor=anchor)


def _line(d,points,width: float=1):
    d.line([(int(x*SCALE),int(y*SCALE)) for x,y in points],fill=0,width=max(1,int(width*SCALE)))


def _ellipse(d,b,fill=None,width: float=1):
    d.ellipse(tuple(int(v*SCALE) for v in b),fill=fill,outline=0,width=max(1,int(width*SCALE)))


def _park(d,x=415,y=91,w=338,h=237):
    """Decorative neighborhood illustration; not an astronomical sky map."""
    ground=y+h*.82
    _line(d,[(x,ground),(x+w,ground)],1.3)
    for sx,sy in [(x+30,y+26),(x+w*.51,y+12),(x+w*.86,y+45)]:
        _line(d,[(sx-3,sy),(sx+3,sy)]);_line(d,[(sx,sy-3),(sx,sy+3)])
    for bx,bw,bh in [(x+105,24,38),(x+132,18,52),(x+155,29,31),(x+187,16,45),(x+208,25,35)]:
        _line(d,[(bx,ground-21),(bx,ground-bh),(bx+bw,ground-bh),(bx+bw,ground-21)])
        for wy in range(int(ground-bh+8),int(ground-25),10):
            _line(d,[(bx+6,wy),(bx+bw-5,wy)],.8)
    for tx,ty,r in [(x+45,ground-66,37),(x+w-40,ground-80,46)]:
        _ellipse(d,(tx-r,ty-r,tx+r,ty+r),255,1.5)
        _line(d,[(tx,ty-11),(tx,ground)],1.6)
        _line(d,[(tx,ty+15),(tx-16,ty-1)],1.2);_line(d,[(tx,ty+28),(tx+19,ty+4)],1.2)
        for dx,dy in [(-15,-9),(13,-14),(-20,12),(18,18)]:
            _line(d,[(tx+dx-4,ty+dy),(tx+dx+4,ty+dy-3)],.8)
    for yy in [ground-21,ground-15,ground-9]:_line(d,[(x+115,yy),(x+175,yy)],1.4)
    for xx in [x+119,x+171]:_line(d,[(xx,ground-23),(xx,ground)],1.5)
    _line(d,[(x+210,ground),(x+190,ground+8),(x+165,ground+16),(x+110,ground+29)])
    _line(d,[(x+247,ground),(x+227,ground+10),(x+220,ground+29)])


def _number(value):
    try:
        n=float(value)
        return round(n) if math.isfinite(n) else None
    except (TypeError,ValueError):return None


def _degree(value):
    n=_number(value)
    return '--' if n is None else str(n)+'°'


def forecast_index(weather, now):
    dates=(weather or {}).get('daily',{}).get('time',[])
    tomorrow=(now.date()+timedelta(days=1)).isoformat()
    return dates.index(tomorrow) if tomorrow in dates else None


def _daily(weather,key,index):
    if index is None:return None
    values=(weather or {}).get('daily',{}).get(key,[])
    return values[index] if index<len(values) else None


def _clock(value):
    try:return datetime.fromisoformat(value).strftime('%I:%M %p').lstrip('0')
    except (TypeError,ValueError):return '--'


def weather_copy(current):
    code=current.get('weather_code')
    feels=_number(current.get('apparent_temperature'))
    if feels is None:feels=_number(current.get('temperature_2m'))
    if code is None:return 'Weather on pause.','Still a good day.','Live conditions unavailable.'
    if code>=95:return 'Stormy skies.','Take care outside.','Check local alerts before heading out.'
    if code>=71 and code<=86 and code not in (80,81,82):
        return 'Snow outside.','Bundle up.','A warm layer and sensible shoes.'
    if code>=51:return 'Rain outside.','Bring an umbrella.','A raincoat if you’re heading out.'
    if code in (45,48):first='A little fog.'
    elif code==3:first='Cloudy skies.'
    elif code in (1,2):first='A little sunshine.'
    else:first='Clear skies.'
    if feels is None:return first,'Take it easy.','Check the forecast before heading out.'
    if feels<35:return first,'Cold air.','Bundle up if you’re heading out.'
    if feels<55:return first,'Cool air.','A jacket if you’re heading out.'
    if feels>=85:return first,'Warm air.','Water and shade if you’re heading out.'
    return first,'Gentle air.','A little time outside might be nice.'


def air_copy(aqi):
    n=_number(aqi)
    if n is None:return 'Air unavailable','No current air-quality reading'
    if n<=50:return 'Good air',f'AQI {n} · A little breathing room'
    if n<=100:return 'Moderate air',f'AQI {n} · Sensitive? Take it easy'
    if n<=150:return 'Mind the air',f'AQI {n} · Limit sensitive exposure'
    if n<=200:return 'Unhealthy air',f'AQI {n} · Reduce outdoor exertion'
    return 'Stay air-aware',f'AQI {n} · Avoid outdoor exertion'


def render(now, weather, aqi=None, battery_percent=None, has_sidebar=False):
    im=Image.new('L',(800*SCALE,480*SCALE),255);d=ImageDraw.Draw(im)
    _text(d,34,22,'THE HOME EDIT',15)
    date=now.strftime('%A, %B ')+str(now.day)
    _text(d,766,23,date.upper(),15,anchor='ra')
    _line(d,[(34,58),(766,58)])
    current=(weather or {}).get('current',{})
    first,second,advice=weather_copy(current)
    _text(d,34,78,first,65,'serif',max_width=365)
    _text(d,34,145,second,65,'serif',max_width=365)
    _text(d,36,230,_degree(current.get('temperature_2m')),59,'serif')
    temp_width=d.textbbox((0,0),_degree(current.get('temperature_2m')),font=font(59,'serif'))[2]/SCALE
    feels=current.get('apparent_temperature')
    _text(d,max(146,46+temp_width),253,'Feels like '+_degree(feels) if feels is not None else 'Feels-like unavailable',19,max_width=245)
    _text(d,36,307,advice,20,max_width=365)
    if not has_sidebar:_park(d)
    _line(d,[(34,357),(766,357)])
    for x,label in [(34,'TOMORROW'),(285,'OUTDOORS'),(536,'REMINDERS')]:_text(d,x,376,label,12)
    i=forecast_index(weather,now)
    hi=_daily(weather,'temperature_2m_max',i);lo=_daily(weather,'temperature_2m_min',i)
    _text(d,34,401,f'{_degree(hi)} / {_degree(lo)}',28,'serif')
    rain=_number(_daily(weather,'precipitation_probability_max',i))
    _text(d,34,440,f'{rain}% chance of rain' if rain is not None else 'Forecast unavailable',15,max_width=235)
    title,detail=air_copy(aqi)
    sunset=_clock(_daily(weather,'sunset',i))
    air_value=_number(aqi)
    if air_value is not None and 0 <= air_value <= 50 and sunset != '--':
        day=(now+timedelta(days=1)).strftime('%a')
        detail=f'AQI {air_value} · {day} sunset {sunset}'
    _text(d,285,401,title,28,'serif',max_width=235)
    _text(d,285,440,detail,15,max_width=235)
    _text(d,536,401,'A note above' if has_sidebar else 'No active notes',28,'serif',max_width=230)
    _text(d,536,440,'Shared notes appear here',15,max_width=230)
    if battery_percent is not None:
        _text(d,766,466,f'Battery {battery_percent}%',9,anchor='ra')
    return im.resize((800,480),Image.Resampling.LANCZOS)


def _wrapped(d,text,f,width):
    lines=[]
    for paragraph in str(text).splitlines():
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if d.textbbox((0,0),candidate,font=f)[2]<=width:
                line=candidate
                continue
            if line:
                lines.append(line);line=''
            # Only split tokens that cannot fit on an otherwise empty line.
            for ch in word:
                if line and d.textbbox((0,0),line+ch,font=f)[2]>width:
                    lines.append(line);line=''
                line+=ch
        lines.append(line)
    return lines


def _fit_lines(d,text,size,face,width,max_lines):
    f=font(size,face,scale=1); lines=_wrapped(d,text,f,width)
    if len(lines)>max_lines:
        lines=lines[:max_lines]
        last=lines[-1].rstrip()
        while last and d.textbbox((0,0),last+'...',font=f)[2]>width:last=last[:-1]
        lines[-1]=last.rstrip()+'...'
    return f,lines


def draw_overlay(im,overlay,image_path=None):
    """Keep slot IDs and expiry semantics while adapting slot geometry to Home Edit."""
    d=ImageDraw.Draw(im);x0,y0,x1,y1=REGIONS[overlay['slot']]
    d.rectangle((x0,y0,x1-1,y1-1),fill=255)
    pad=8; x=x0+pad; y=y0+pad; width=x1-x0-2*pad
    if image_path:
        with Image.open(image_path) as source:
            art=source.convert('L');art.thumbnail((width,(y1-y0)//2))
            im.paste(art,(x,y));y+=art.height+6
    title=overlay.get('title') or 'A note for home'
    title_size=28 if overlay['slot']!='fullscreen' else 40
    title_font,lines=_fit_lines(d,title,title_size,'serif',width,1)
    for line in lines:d.text((x,y),line,font=title_font,fill=0);y+=title_size+5
    size=20 if overlay['slot']!='sidebar' else 18
    if overlay['slot']=='fullscreen':size=27
    available=y1-y-pad
    max_lines=max(1,available//(size+5))
    body_font,lines=_fit_lines(d,overlay.get('text') or '',size,'sans',width,max_lines)
    for line in lines:
        if y+size>y1-pad:break
        d.text((x,y),line,font=body_font,fill=0);y+=size+5
