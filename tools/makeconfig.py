import json, os, os.path, argparse, glob, re, ast

parser = argparse.ArgumentParser(description='Generate JSON configuration file for SystemDataScope')
parser.add_argument('root_dir', type=str,
                    help='Root directory with collectd RRD databases, for example /tmp/collectd/Jolla')

args = parser.parse_args()

Root = args.root_dir
os.chdir(Root)

Config = {}

Config["variables"] = {
    "COLOR_BACKGROUND": "#00000000",
    "COLOR_CANVAS": "#00000000",
    "COLOR_FONT": "#000000FF",
    "COLOR_AXIS": "#000000FF",
    "COLOR_ARROW": "#000000FF",
    "COLOR_LINE_SINGLE": "#0000FFFF",
    "COLOR_LINE_SINGLE_SUB": "#0000FF80",

    "LINE_WIDTH_PRIMARY": "3",
    "LINE_WIDTH_SECONDARY": "1"    
    }

Config["page"] = {
    
    "title": "Overview",
    "plots": [
    ]
}

defColors = "--color BACK$COLOR_BACKGROUND$ --color SHADEA$COLOR_BACKGROUND$ --color SHADEB$COLOR_BACKGROUND$ --color CANVAS$COLOR_CANVAS$  "
defColors += "--color FONT$COLOR_FONT$ --color AXIS$COLOR_AXIS$ --color ARROW$COLOR_ARROW$ "

######################################################################################
## Helper classes

class ColorSingle:
    def __init__(self, color):
        self.color = color

    def set_number_of_lines(self, n):
        # noop
        self.n = n

    def get_color(self, i):
        return self.color

class Colors:
    # internally stored as RGBA integers
    # Colorschemes from http://colorbrewer2.org/ , qualitative
    def __init__(self, last_transparent = False):
        self.colors = None
        self.n = None
        self.last_transparent = last_transparent

        self.colorschemes = {}
        for cbrewer in [ "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)'",
                         "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)'",
                         "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)'",
                         "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)','rgb(255,255,51)'",
                         "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)'",
                         "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)','rgb(247,129,191)'",
                         "'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)','rgb(247,129,191)','rgb(153,153,153)'"
        ]:
            cbrewer = "[ " +  cbrewer.replace("'rgb(", "[" ).replace(")'", "]" ) + " ]"
            colors = ast.literal_eval( cbrewer )
            for i in colors: i.append(255)
            self.colorschemes[ len(colors) ] = colors
            
    def set_number_of_lines(self, n):
        self.n = n
        if self.last_transparent: k = n-1
        else: k = n

        if self.colorschemes.has_key(k):
            self.colors = self.colorschemes[k]
        elif k < min(self.colorschemes.keys()):
            self.colors = self.colorschemes[ min(self.colorschemes.keys()) ]
        else:
            self.colors = self.colorschemes[ max(self.colorschemes.keys()) ]

    def makestr(self, c, opacity):
        s = "#"
        for i in c[:-1]:
            s += ("%02X" % int(round(i)) )
        s += ("%02X" % int(round(c[-1]*opacity)) )
        return s

    def get_color(self, i, opacity=1.0):
        if i == 0: return self.makestr(self.colors[0], opacity)
        if self.last_transparent:
            if i >= self.n-1: return self.makestr([0,0,0,0], opacity)
            elif i == self.n-2: return self.makestr(self.colors[-1], opacity)
        else:
            if i >= self.n-1: return self.makestr(self.colors[-1], opacity)

        if self.last_transparent: nc = self.n-2
        else: nc = self.n-1

        dline = float(i) / float(nc)
        color0 = int( (len(self.colors) - 1) * dline )
        factor = (len(self.colors) - 1) * dline - color0

        c = []
        for i in range(len(self.colors[color0])):            
            c.append( (1-factor)*self.colors[color0][i] + factor*self.colors[color0+1][i] )
        return self.makestr(c, opacity)

    
class StackOrLines:
    def __init__(self, col, isStack = False, minmax = False, t = "LINE"):
        self.lines = []
        self.gt = t
        self.colors = col
        self.isStack = isStack
        self.minmax = minmax

    def add(self, name, width, options, extra="", makeLine=False):
        self.lines.append( { "name": name,
                             "width": width,
                             "options": options,
                             "extra": extra,
                             "makeLine": makeLine } )
        
    def str(self):
        s = ""
        self.colors.set_number_of_lines(len(self.lines))
        if self.minmax:
            for idx, i in enumerate(self.lines):
                s += "LINE:" + i["name"] + "_min AREA:" + i["name"] + "_max_min_delta" + self.colors.get_color(idx, 0.5) + "::STACK "
                
        for idx, i in enumerate(self.lines):
            color = self.colors.get_color(idx) 
            s += self.gt
            if self.gt == "LINE": s += i["width"]
            s += ":" + i["name"] + color + ":" + i["options"]
            if self.isStack and idx > 0 and not i["makeLine"]: s += ":STACK"
            s += " " + i["extra"] + " "
            
        return s    
        
######################################################################################
# Colorschemes. If more are needed, see at http://colorbrewer2.org/

# http://colorbrewer2.org/?type=qualitative&scheme=Set1&n=8
cmap = [ [228,26,28,255],[55,126,184,255],[77,175,74,255],[152,78,163,255],[255,127,0,255],[255,255,51,255],[166,86,40,255],[247,129,191,255] ]
cs = Colors( )
csTr = Colors( True )
csSingle = ColorSingle( "$COLOR_LINE_SINGLE$" )

######################################################################################
Units = { "DEFAULT": "",
          "CPU": "%",
          "Battery/voltage": "V",
          "Battery/current": "A",
          "Context/context_switch": "1/s",
          "Entropy/entropy": "bits",
          "Memory": "bytes",
          "Network/octets": "bytes/s",
          "NetworkTotal/octets": "B",
          "Network": "1/s",
          "NetworkTotal": ""
}

Formats = { "DEFAULT": "%5.2lf",
            "Battery/voltage": "%1.3lf%S",
            "Battery/current": "%1.0lf%S",
            "Context/context_switch": "%1.0lf%S",
            "Entropy/entropy": "%1.0lf%S",
            "Memory": "%4.0lf%S",
            "Load": "%5.2lf",
            "Network/octets": "%6.0lf%S",
            "Network/packets": "%6.0lf%S",
            "Network": "%6.2lf%S"
}

def getit(name, D):
    if name in D: return D[name]
    sname = name.split("/")[0]
    if sname in D: return D[sname]
    return D["DEFAULT"]

def getunit(name): return getit(name, Units)
def getf(name): return getit(name, Formats)

######################################################################################
# Helper function for a single value plot
def maketypesplot(name, g, Type, Title = None):

    fullname = Type + "/" + name
    
    f = getf(fullname)
    u = getunit(fullname)
    frm = f + u
    
    command_def = '-t " '
    if Title is not None: command_def += Title
    else: command_def += Type + " " + name

    if len(u) > 0: command_def += ", " + u
    command_def += '"  '  + " " + defColors
    
    command_line = ""
    files = []
    s = StackOrLines(csSingle)
    command_def += "DEF:" + name + "=" + g + ":value:AVERAGE "
    command_def += "DEF:" + name + "_min=" + g + ":value:MIN "
    command_def += "DEF:" + name + "_max=" + g + ":value:MAX "
    command_def += "CDEF:" + name + "_max_min_delta=" + name + "_max," + name + "_min,- "
    command_def += "LINE:" + name + "_min AREA:" + name + "_max_min_delta$COLOR_LINE_SINGLE_SUB$::STACK "
    s.add( name, "$LINE_WIDTH_PRIMARY$", '" \\l"',
           "COMMENT:\\u GPRINT:"+name+":AVERAGE:\"Avr " + f + "\" GPRINT:"+name+"_min:MIN:\"Min " + f +
           "\" GPRINT:"+name+"_max:MAX:\"Max " + f + "\" GPRINT:"+name+":LAST:\"Last " + f + "\\r\" ")
    files.append(g)

    command_line = s.str()

    gt = { "command": command_def + command_line,
           "files": files }
    plot = { "type": fullname }

    return gt, plot

# Helper function to print table heading
def makeheads(l):
    s = ''
    fmt = '%' + str(l) + 's'
    heads = ["Avr", "Min", "Max", "Last"]
    for i, t in enumerate(heads):
        s += 'COMMENT:"' + (fmt % t)
        if i == len(heads)-1: s += '\\r" '
        else: s += '" '
    return s

                
######################################################################################
# Start definition of types                
Config["types"] = {}


               
######################################################################################
# CPU

CpuPlots = { "subplots": { "title": "CPU details", "plots": [ { "type": "CPU/overview" } ] } }

# CPU overview
command_def = "-t \"CPU usage, " + getunit("CPU") + "\" --upper-limit 100 --lower-limit 0 --rigid " + defColors
command_line = ""
files = []
s = StackOrLines( csTr, isStack = True, t = "AREA" )
cpustates_fr = [ 0, ["interrupt", "softirq", "steal", "wait", "system"] ]
cpustates_end = [ len(cpustates_fr) + 100, ["user", "nice", "idle"] ]
cpustates_other = len(cpustates_fr) + 50
cpustates = []
for g in glob.glob( "cpu/*.rrd" ):
    m = re.search( "^cpu.*/.*-(.*).rrd", g ).group(1)
    for k in [ cpustates_fr, cpustates_end ] :
        if m in k[1]:
            cpustates.append( [ k[0] + k[1].index( m ), g ] )
    if m not in cpustates_fr[1] and m not in cpustates_end[1]:
        cpustates.append( [ cpustates_other, g ] )

cpustates.sort()

command_def += makeheads(6)
for gcpu in cpustates:
    g = gcpu[1]
    name = re.search( "^cpu.*/.*-(.*).rrd", g ).group(1)
    command_def += "DEF:" + name + "=" + g + ":value:AVERAGE "
    s.add( name, "$LINE_WIDTH_PRIMARY$", "\"" + name + '\\l"',
           "COMMENT:\\u GPRINT:"+name+":AVERAGE:\"%6.0lf\" GPRINT:"+name+":MIN:\"%6.0lf\" GPRINT:"+name+":MAX:\"%6.0lf\" GPRINT:"+name+":LAST:\"%6.0lf\\r\" " )
    files.append(g)

command_line = s.str()
Config["types"]["CPU/overview"] = { "command": command_def + command_line,
                                    "files": files }

CpuPlots["type"] = "CPU/overview"

# Make CPU subplots
cpustates.reverse()
for gcpu in cpustates:
    g = gcpu[1]
    name = re.search( "^cpu.*/.*-(.*).rrd", g ).group(1)
    command_def = "-t \"CPU " + name + ", " + getunit("CPU") + "\" --upper-limit 100 --lower-limit 0 --rigid " + defColors
    command_line = ""
    files = []
    s = StackOrLines(csSingle)
    command_def += "DEF:" + name + "=" + g + ":value:AVERAGE "
    command_def += "DEF:" + name + "_min=" + g + ":value:MIN "
    command_def += "DEF:" + name + "_max=" + g + ":value:MAX "
    command_def += "CDEF:" + name + "_max_min_delta=" + name + "_max," + name + "_min,- "
    command_def += "LINE:" + name + "_min AREA:" + name + "_max_min_delta$COLOR_LINE_SINGLE_SUB$::STACK "
    s.add( name, "$LINE_WIDTH_PRIMARY$", '"\\l"',
           "COMMENT:\\u GPRINT:"+name+":AVERAGE:\"Avr %1.0lf\" GPRINT:"+name+"_min:MIN:\"Min %1.0lf\" GPRINT:"+name+"_max:MAX:\"Max %1.0lf\" GPRINT:"+name+":LAST:\"Last %1.0lf\\r\" ")
    files.append(g)

    command_line = s.str()

    Config["types"]["CPU/" + name] = { "command": command_def + command_line,
                                       "files": files }
    CpuPlots["subplots"]["plots"].append( { "type": "CPU/" + name } )

# Add all CPU plots
Config["page"]["plots"].append( CpuPlots )


######################################################################################
# Battery 
    
BatteryPlots = { "subplots": { "title": "Battery details", "plots": [ ] } }

for g in glob.glob( "battery-0/*.rrd" ):
    name = re.search( "^battery.*/(.*).rrd", g ).group(1)
    gt, plot = maketypesplot( name, g, "Battery" )

    Config["types"]["Battery/" + name] = gt
    BatteryPlots["subplots"]["plots"].append( plot )

# Add all Battery plots
BatteryPlots["type"] = "Battery/voltage"
Config["page"]["plots"].append( BatteryPlots )


######################################################################################
# Storage

Plots = { "subplots": { "title": "Storage details", "plots": [ ] } }

for gd in glob.glob( "df-*" ):
    part_name = re.search( "^df-(.*)", gd ).group(1)

    command_def = '-t "Storage ' + part_name +  '" --lower-limit 0 ' + defColors
    command_line = ""
    command_def += makeheads(4+1)
    files = []
    s = StackOrLines( cs, isStack = True, t = "AREA" )

    allGs = []
    for g in glob.glob( gd + "/*.rrd" ): allGs.append(g)
    allGs.reverse() # to get free as a last
    
    for g in allGs:
        name = re.search( "^df-.*/df_complex-(.*).rrd", g ).group(1)
        command_def += "DEF:" + name + "=" + g + ":value:AVERAGE "
        s.add( name, "$LINE_WIDTH_PRIMARY$", "\"" + name + '\\l"',
               "COMMENT:\\u GPRINT:"+name+":AVERAGE:\"%4.1lf%S\" GPRINT:"+name+":MIN:\"%4.1lf%S\" GPRINT:"+name+":MAX:\"%4.1lf%S\" GPRINT:"+name+":LAST:\"%4.1lf%S\\r\" " )
        files.append(g)
    
    command_line = s.str()

    Config["types"]["Storage/" + part_name] = { "command": command_def + command_line,
                                                "files": files }

    Plots["subplots"]["plots"].append( {"type": "Storage/" + part_name} )

Plots["type"] = "Storage/root"
Config["page"]["plots"].append( Plots )


######################################################################################
# Memory

Plots = { "subplots": { "title": "Memory details", "plots": [ { "type": "Memory/overview" } ] } }

# Memory overview
command_def = '-t "Memory overview, bytes" --lower-limit 0 ' + defColors
command_line = ""
files = []
s = StackOrLines( cs, isStack = True, t = "AREA" )

memory_fr = [ 0, ["slab_unrecl", "slab_recl", "used", "buffered", "system"] ]
memory_end = [ len(memory_fr) + 100, ["cached", "free"] ]
memory_other = len(memory_fr) + 50
memory = []
for g in glob.glob( "memory/*.rrd" ):
    m = re.search( "^memory/.*-(.*).rrd", g ).group(1)
    for k in [ memory_fr, memory_end ] :
        if m in k[1]:
            memory.append( [ k[0] + k[1].index( m ), g ] )
    if m not in memory_fr[1] and m not in memory_end[1]:
        memory.append( [ memory_other, g ] )

memory.sort()

command_def += makeheads(4+1)
for gt in memory:
    g = gt[1]
    name = re.search( "^memory/.*-(.*).rrd", g ).group(1)
    command_def += "DEF:" + name + "=" + g + ":value:AVERAGE "
    s.add( name, "$LINE_WIDTH_PRIMARY$", "\"" + name + '\\l"',
           "COMMENT:\\u GPRINT:"+name+":AVERAGE:\"%4.0lf%S\" GPRINT:"+name+":MIN:\"%4.0lf%S\" GPRINT:"+name+":MAX:\"%4.0lf%S\" GPRINT:"+name+":LAST:\"%4.0lf%S\\r\" " )
    files.append(g)

command_line = s.str()

Config["types"]["Memory/overview"] = { "command": command_def + command_line,
                                       "files": files }

# detailed plots
memory.reverse()
for gm in memory:
    g = gm[1]
    name = re.search( "^memory/.*-(.*).rrd", g ).group(1)
    gt, plot = maketypesplot( name, g, "Memory" )

    Config["types"]["Memory/" + name] = gt
    Plots["subplots"]["plots"].append( plot )


Plots["type"] = "Memory/overview"
Config["page"]["plots"].append( Plots )

######################################################################################
Plots = { "subplots": { "title": "Network details", "plots": [ ] } }

for CNet in glob.glob("interface-*/if_octets.rrd"):
    intname = re.search( "^interface-(.*)/if_octets.rrd", CNet ).group(1)

    SubPlots = { "subplots": { "title": "Network details: " + intname, "plots": [ ] } }
    
    for g in glob.glob("interface-" + intname + "/if_*.rrd"):
        name = re.search( "^interface-.*/if_(.*).rrd", g ).group(1)
        fullname = "Network/" + intname + "/" + name
        f = getf("Network/" + name)
        u = getunit("Network/" + name)

        if name == "octets": hname = "traffic"
        else: hname = name
    
        command_def = '-t "Network ' + intname + ' ' + hname + ", " + u + '" --lower-limit 0 ' + defColors + makeheads(7)
        command_line = ""
        command_extra = ""
        files = [g]
        s = StackOrLines( cs, minmax=True )
        for li, data_type in  enumerate([ "tx", "rx" ]):
            frm = f + u
            humandt = { "tx": "Outgoing", "rx": "Incoming" }[data_type]

            command_def += "DEF:" + data_type + "=" + g + ":" + data_type + ":AVERAGE "
            command_def += "DEF:" + data_type + "_min=" + g + ":" + data_type + ":MIN "
            command_def += "DEF:" + data_type + "_max=" + g + ":" + data_type + ":MAX "
            command_def += "CDEF:" + data_type + "_max_min_delta=" + data_type + "_max," + data_type + "_min,- "
            command_def += "VDEF:" + data_type + "_total=" + data_type + ",TOTAL "
                
            s.add( data_type, "$LINE_WIDTH_PRIMARY$", '"' + humandt + '\\l"',
                   "COMMENT:\\u GPRINT:"+data_type+":AVERAGE:\"" + f + "\" GPRINT:"+data_type+"_min:MIN:\"" + f +
                   "\" GPRINT:"+data_type+"_max:MAX:\"" + f + "\" GPRINT:"+data_type+":LAST:\"" + f + "\\r\" " + " " 
            )

            command_extra += 'GPRINT:' + data_type + '_total:"' + humandt + ' Total %8.0lf%s' + getunit("NetworkTotal/" + name) + '\\r" ' 

        command_line = s.str() + command_extra

        gt = { "command": command_def + command_line,
               "files": files }
        plot = { "type": fullname }

        Config["types"][fullname] = gt
        SubPlots["subplots"]["plots"].append( plot )

    SubPlots["type"] = "Network/" + intname + "/octets"
    Plots["subplots"]["plots"].append( SubPlots )
    if not Plots.has_key("type"): Plots["type"]  = "Network/" + intname + "/octets"
        
Config["page"]["plots"].append( Plots )
######################################################################################
# Load
Plots = { "subplots": { "title": "Load details", "plots": [ { "type": "Load/load" } ] } }

command_def = '-t "Load" --lower-limit 0 ' + defColors + makeheads(5)
command_line = ""
files = ["load/load.rrd"]
s = StackOrLines( cs, minmax=True )
for li, load_type in  enumerate([ "shortterm", "midterm", "longterm" ]):
    Type = "Load"
    name = load_type
    g = "load/load.rrd"

    fullname = Type + "/" + name
    
    f = getf(fullname)
    u = getunit(fullname)
    frm = f + u
    
    command_def += "DEF:" + name + "=" + g + ":" + name + ":AVERAGE "
    command_def += "DEF:" + name + "_min=" + g + ":" + name + ":MIN "
    command_def += "DEF:" + name + "_max=" + g + ":" + name + ":MAX "
    command_def += "CDEF:" + name + "_max_min_delta=" + name + "_max," + name + "_min,- "
    s.add( name, "$LINE_WIDTH_PRIMARY$", '"' + name + '\\l"',
           "COMMENT:\\u GPRINT:"+name+":AVERAGE:\"" + f + "\" GPRINT:"+name+"_min:MIN:\"" + f +
           "\" GPRINT:"+name+"_max:MAX:\"" + f + "\" GPRINT:"+name+":LAST:\"" + f + "\\r\" ")

command_line = s.str()

gt = { "command": command_def + command_line,
       "files": files }
plot = { "type": fullname }

Config["types"]["Load/load"] = gt

Plots["type"] = "Load/load"
Config["page"]["plots"].append( Plots )

#### Other Load related graphs

g = "contextswitch/contextswitch.rrd"
name = "context_switch"
gt, plot = maketypesplot( name, g, "Context", "Context switch" )
Config["types"]["Context/" + name] = gt
Plots["subplots"]["plots"].append( plot )

g = "entropy/entropy.rrd"
name = "entropy"
gt, plot = maketypesplot( name, g, "Entropy", "Entropy" )
Config["types"]["Entropy/" + name] = gt
Plots["subplots"]["plots"].append( plot )


###################################################
# Misc

Plots = { }


###################################################
# uptime needs some math
g = "uptime/uptime.rrd"
name = "uptime"
f = getf(name)
u = getunit(name)
frm = f + u

command_def = '-t "Uptime, days" ' + defColors
command_line = ""
files = []
s = StackOrLines(csSingle)
command_def += "DEF:" + name + "_data=" + g + ":value:AVERAGE "
command_def += "CDEF:" + name + "=" + name + "_data,86400,/ "
s.add( name, "$LINE_WIDTH_PRIMARY$", '"\\l"',
       "COMMENT:\\u GPRINT:"+name+":LAST:\"Current " + frm + "\\r\" ")
files.append(g)

command_line = s.str()

gt = { "command": command_def + command_line,
       "files": files }
plot = { "type": "Uptime/" + name }

Config["types"]["Uptime/" + name] = gt
Plots["type"] = "Uptime/" + name 

# Add all Misc plots
Config["page"]["plots"].append( Plots )



# Print resulting JSON configuration
print json.dumps(Config, indent=3)
