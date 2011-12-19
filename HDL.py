import sublime, sublime_plugin
import re
import string

class VHDLCompletion(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if prefix.lower() == 'entity':
            return [('entity instantiate x','entity work.${1:x arg1}${2:(${3})}'), ('entity instantiate y','entity work.y')]
        else:
            return []

# Scopes to match
GENERIC_LIST            = 'meta.block.generic_list.vhdl'
PORT_LIST               = 'meta.block.port_list.vhdl'
ENTITY_INSTANTIATION    = 'meta.block.entity_instantiation.vhdl'
COMPONENT_INSTANTIATION = 'meta.block.component_instantiation.vhdl'
PARENTHETICAL_LIST      = 'meta.block.parenthetical_list.vhdl'
ARCHITECTURE            = 'meta.block.architecture'

# Checks to see if the region is within the passed scope
def check_scope(view,region,scope):
    current_scope = view.scope_name(region.a)
    if re.search(scope, current_scope, re.IGNORECASE) == None:
        return False
    return True

# Find the maximum length to match pattern with lines, and
# then add spaces to pad out until the maximum length
def line_up(pattern,lines):
    # Initialize min/max variables
    min = None
    max = None

    # Find the min/max values for the patterns
    for l in lines:
        m = re.search( pattern, l, re.IGNORECASE )
        if m != None:
            if min == None or len(m.group(0)) < min:
                min = len(m.group(0))
            if max == None or len(m.group(0)) > max:
                max = len(m.group(0))
    
    #print 'min: ' + str(min) + ' max: ' + str(max) + ' pattern: ' + pattern

    # As long as we found something and they aren't the same...
    if min != None and max != None and min != max:
        # Add in spaces to get the counts to match
        for i,l in enumerate(lines):
            m = re.search( pattern, l, re.IGNORECASE)
            if m!= None:
                extra = max - len(m.group(0))
                lines[i] = string.replace(l, m.group(0), m.group(0) + ' '*extra)

# Align the region with the lines based on scope
def align_and_replace(view, edit, region, lines):
        # Normalize the leading whitespace for lines which have a word character in them
        if check_scope(view, region, ARCHITECTURE) == False:
            line_up( '^(\s+)(?=\w)', lines )
        else:
            line_up( '^(\s+)(?=signal)', lines )

        # If region is in a generic or port list, then align first colon
        if check_scope(view, region, GENERIC_LIST) or check_scope(view, region, PORT_LIST):
            # Normalizing the length between the stuff leading up to the colon, and the stuff after the colon
            # ([^:]+):(.+$)
            line_up( '([^:]+)(?=:)', lines )
            #print "Aligning on first colon"

        # If region is in a port list, then align the direction plus the word after the direction
        if check_scope(view, region, PORT_LIST):
            line_up( '([^:]+:\s*)(?=in|out|inout|buffer)', lines )
            line_up( '([^:]+:\s*(in|out|inout|buffer))', lines )
            #print "Aligning on in/out/inout/buffer"

        # If region is in a generic or port list, then align on :=
        if check_scope(view, region, GENERIC_LIST) or check_scope(view, region, PORT_LIST):
            line_up( '(.+?)(?=:=)', lines )
            #print "Aligning on :="

        # If region is in a generic or port map, then align on =>
        if check_scope(view, region, COMPONENT_INSTANTIATION) or check_scope(view, region, ENTITY_INSTANTIATION):
            line_up( '[^=]+(?==>)', lines )
            #print "Aligning on =>"

        if check_scope(view, region, ARCHITECTURE):
            # Signals
            line_up( '(\s*signal[^:]+)(?=:)', lines )
            line_up( '(\s*signal.+?)(?=:=)', lines )
            # Constants
            line_up( '(\s*constant[^:]+)(?=:)', lines )
            line_up( '(\s*constant.+?)(?=:=)', lines )
            #print 'Aligning architecture signals'

        # Concatenate all the lines
        newtext = ''
        for l in lines:
            newtext = newtext + l ;
            if l != lines[-1]:
                newtext = newtext + '\n'
        
        # Finish the edit
        view.replace(edit,region,newtext)

# Align whole file
class HdlAlignFile(sublime_plugin.TextCommand):

    def run(self,edit):
        regions = self.view.find_by_selector(PARENTHETICAL_LIST)
        print 'Found ' + str(len(regions)) + ' parenthetical lists'
        for region in regions:
            print 'xy: ' + str(self.view.rowcol(region.a))
            # if check_scope(self.view, region, GENERIC_LIST):
            #     print 'Found generic list  : ' + str(self.view.rowcol(region.a))
            #     text = self.view.substr(region)
            #     lines = re.split('\n',text)
            #     align_and_replace(self.view, edit, region, lines)
            # elif check_scope(self.view, region, PORT_LIST):
            #     print 'Found port list     : ' + str(self.view.rowcol(region.a))
            #     text = self.view.substr(region)
            #     lines = re.split('\n',text)
            #     align_and_replace(self.view, edit, region, lines)
            # elif check_scope(self.view, region, ENTITY_INSTANTIATION):
            #     print 'Found entity inst   : ' + str(self.view.rowcol(region.a))
            #     text = self.view.substr(region)
            #     lines = re.split('\n',text)
            #     align_and_replace(self.view, edit, region, lines)
            # elif check_scope(self.view, region, COMPONENT_INSTANTIATION):
            #     print 'Found component inst: ' + str(self.view.rowcol(region.a))
            #     text = self.view.substr(region)
            #     lines = re.split('\n',text)
            #     align_and_replace(self.view, edit, region, lines)
            # else:
            #     print 'Skipping region     : ' + str(self.view.rowcol(region.a))

# Align appropriately when carat is in a:
#   - generic list
#   - port list 
#   - entity instantiation
#   - component instantiation
#   - architecture
class HdlAlignRegion(sublime_plugin.TextCommand):

    def run(self,edit,cursor=None):
        # Find the current carat location(s)
        carats = self.view.sel()

        # For all the carats...
        for carat in carats:
            # Extract out the region of the current cursor location
            regions = self.view.find_by_selector(PARENTHETICAL_LIST)
            region = None
            for r in regions:
                if r.contains(carat):
                    region = r
        
            # Make sure we're in a parenthetical list
            if region == None:
                regions = self.view.find_by_selector(ARCHITECTURE)
                for r in regions:
                    if r.contains(carat):
                        region = r
            
            if region == None:
                print 'Not within a parenthetical list or arhchitecture'
                return

            # Get the total scope and the text associated with it
            scope = self.view.scope_name(region.a)
            text = self.view.substr(region)

            # Split up the lines based on newlines
            lines = re.split('\n',text)

            # The main stuff
            align_and_replace(self.view, edit, region, lines)
