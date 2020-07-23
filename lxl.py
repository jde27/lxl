from subprocess import run, PIPE
import itertools
import more_itertools as mit
import random
import sys
import yaml

theorem_list = ['Lemma', 'Theorem', 'Corollary', 'Definition', 'Example', 'Proposition', 'Proof', 'Remark']
meta_tags =  ['title', 'author', 'description']
img_path = './img/'

input_file = sys.argv[1]
output_mathml = input_file[:-4] + '.html'
output_accessible = input_file[:-4] + '_accessible' + '.html'

def split_by_char(_list, char):
    return [list(y)
            for x, y in itertools.groupby(_list,
                                          lambda z: z == char)
            if not x]

class Equation:
    '''Equation:

    Equations can be entered in the form

      \(\frac{-b\pm\sqrt{b^2-4ac}}{2a}$minus b plus or minus square root b squared minus 4 a c, all over 2 a$\)

    or

      $\frac{-b\pm\sqrt{b^2-4ac}}{2a}\(minus b plus or minus square root b squared minus 4 a c, all over 2 a\)$

    Depending on which mode your Document is in.

    You can always use \[ \] (and if you're in $ mode you can also use $$)

    The extra delimiters inside the equation are optional and allow you to enter alt text for your equation.
    If you omit them then the alt text will simply be the text of your equation, e.g.
    $x$ will give alt text x.
    '''
    def __init__(self, text):
        '''Create an equation with a string of text.

        This text can be added to and the Equation will only "work"
        (e.g. parse as LaTeX) if it is subsequently closed.

        '''
        self.text = text

    def close(self):
        '''Use when all text has been entered and Equation is ready to be processed.'''
        self.body = self.text[1:-1] # the equation without its outermost delimiters
        if '$' in self.body:
            # $...$ is being used to insert alt text
            partition = split_by_char(self.body, '$')
        elif '\(' in self.body:
            # \(...\) is being used to insert alt text
            partition = split_by_char(self.body[:-1], '\(')
        else:
            # use self.body as alt text
            partition = [self.body, self.body]
        self.latex = str(self.text[0]) + ''.join(partition[0]) + str(self.text[-1])
        self.alt_text = ''.join(partition[1])
        
    def latexml(self):
        '''Get MathML code for self using LaTeXML.'''
        latex_code = self.macros()
        xml_code = run(["latexmlmath",
                        "--pmml",
                        "-",
                        latex_code], stdout=PIPE)
        mathml_code = xml_code.stdout.decode('UTF-8')[39:]
        return mathml_code

    def macros(self):
        '''Implement some basic macros

        e.g. \CC --> \mathbf{C}, 

        or turn \begin{pmatrix} into something that LaTeXML can handle.

        These macros are not failsafe: e.g. if you have nested
        pmatrices or commands like \CCommand then this will break it.

        Feel free to add your own.

        '''
        latex_code = ''.join(self.latex)

        while '\\begin{pmatrix}' in latex_code:
            i = latex_code.find('\\begin{pmatrix}')
            pre_string = latex_code[:i]
            remaining_string = latex_code[i+14:]
            if '\\\\' in remaining_string:
                j = remaining_string.find('\\\\')
            else:
                j = len(remaining_string)+1
            if '\\end{pmatrix}' in remaining_string:
                k = remaining_string.find('\\end{pmatrix}')
            else:
                k = len(remaining_string+1)
            cut_string = remaining_string[:min(j,k)]
            num_cols = cut_string.count('&') + 1
            latex_code = pre_string + '\\left(\\begin{array}[' + 'c'*num_cols + ']' + remaining_string

        latex_code = latex_code.replace('\\end{pmatrix}', '\\end{array}\\right)')
        for char in ['R', 'C', 'Q', 'Z']:
            latex_code = latex_code.replace('\\'+char*2, '\mathbf{'+char+'}')
            
        return latex_code
    
    def tikz_str(self):
        return self.latex
    
    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self.accessible('alt')

    def accessible(self, modus):
        if modus == 'mathml':
            return self.latexml()
        elif modus == 'alt':
            return self.alt_text

class Element:
    '''Parent class of Line and Environment

    Defines trivial functions in the interests of polymorphism
    (e.g. can write x.equify() and not worry about whether x is a Line
    or an Environment). These get redefined when it's important.

    '''
    def __init__(self):
        pass

    def process(self):
        pass

    def taggify(self):
        pass

    def merge(self):
        pass
    
    def equify(self):
        pass

    def split_paragraphs(self):
        return [self]

    def make_paragraphs(self):
        pass
    
    def group_list_items(self):
        pass
    
class Line(Element):
    def __init__(self, chars, char_map):
        '''Line object.

        chars is a list of characters (some of which are 'special', like '\(')

        char_map is a list of T/F values or '\n' characters. True
        means this character is inside an LaTeX equation.

        '''
        self.name = ''
        self.chars = chars
        self.char_map = char_map

        non_whitespace_indices = [i for i in range(0,len(chars))
                                  if not(chars[i].isspace())]
        if non_whitespace_indices:
            self.indent = min(non_whitespace_indices)
        else:
            self.indent = None

    def is_empty(self):
        '''Test for lines comprising whitespace only.'''
        return self.indent == None
            
    def is_env(self):
        '''Test if self is a new environment.

        True if self is a non-blank line whose first non-whitespace
        character is a # not in an equation.

        '''
        i = self.indent
        if i != None:
            return self.chars[i] == '#' and self.char_map[i] == False
        else:
            return False

    def is_star(self, i):
        '''True if the ith character of self is a star not in an equation.'''
        return self.chars[i] == '*' and self.char_map[i] == False
    
    def stars(self):
        '''Count the number of * characters at the beginning of self.'''
        star_indices = [i for i in range(0,len(self.chars))
                        if self.is_star(i)]
        
        if star_indices:
            # If there are any stars on the line...
            if min(star_indices) == 0:
                # If there is a * character at the beginning of the line
                # return the number of * in the initial clump of * characters
                star_groups = [list(group) for group in mit.consecutive_groups(star_indices)]
                return len(star_groups[0])
            else:
                return 0
        else:
            return 0

    def envify(self):
        '''Turns lines of the form '# environment' into Environments.

        Definitely needs a return value as it's not an in-place
        modification.

        '''
        i = self.indent
        if self.is_env():
            return Environment('# ' + ''.join(self.chars[i+2:]), i)
        else:
            return self

    def equify(self):
        '''Extracts LaTeX from lines

        Modifies self.chars and self.chars_map so that each equation
        becomes a single char of type Equation (with char_map value
        True).

        '''
        new_line = []
        new_map = []
        in_eq = False
        
        for x in range(0,len(self.chars)):
            if not in_eq:
                if self.char_map[x] == True:
                    # Start new equation
                   new_line += [Equation([self.chars[x]])]
                   new_map += [True]
                   in_eq = True
                else:
                    new_line +=[self.chars[x]]
                    new_map += [False]
            else:
                if self.char_map[x] == True:
                    # Add to currently open equation
                    new_line[-1].text += [self.chars[x]]
                else:
                    # Close currently open equation
                    new_line[-1].close()
                    new_line += [self.chars[x]]
                    new_map += [False]
                    in_eq = False
                    
        self.chars = new_line
        self.char_map = new_map

    def split_paragraphs(self):
        '''Splits line into paragraphs according to parbreaks

        parbreak characters are inserted by merge() when it finds
        lines separated by lines of whitespace.

        '''
        par_texts = [Paragraph(line) for line in split_by_char(self.chars, 'parbreak')]
        pars = [Environment('# p') for x in par_texts]
        for x in range(0,len(par_texts)):
            pars[x].contents = [par_texts[x]]

        # Definitely needs a return value: this is not an in-place
        # modification of self, but splits self into a list of
        # paragraphs.
        return pars

    def tikz_str(self):
        strs = []
        for x in self.chars:
            if type(x).__name__ == 'Equation':
                strs += [x.tikz_str()]
            else:
                strs += [str(x)]
        return ''.join([x for x in strs])
    
    def __str__(self):
        return self.__repr__()
        
    def __repr__(self):
        return self.accessible('mathml')

    def accessible(self, modus):
        strs = ''
        for x in self.chars:
            if type(x).__name__ == 'str':
                strs += x
            else:
                strs += x.accessible(modus)
        return strs

    def __add__(self, other):
        '''Merge lines (adding a space between)

        The only complication is to figure out whether the line break
        is in the middle of an equation or not, so how to assign the
        char_map to the new whitespace character.

        '''
        new_chars = self.chars + [' '] + other.chars
        
        if self.char_map[-1] and other.char_map[0]:
            if self.chars[-1] in ['\\)', '\\]', '$', '$$']:
                intermediate = False
            else:
                intermediate = True
        else:
            intermediate = False

        new_map = self.char_map + [intermediate] + other.char_map
        
        return Line(new_chars, new_map)
    
    @classmethod
    def empty_line(cls):
        '''Never leave blank lines in the middle of equations'''
        return cls(['parbreak'], [False])

class Paragraph(Element):
    def __init__(self, chars):
        self.name = 'p'
        self.chars = chars
        
    def __str__(self):
        return self.__repr__()
        
    def __repr__(self):
        return self.accessible('mathml')

    def accessible(self, modus):
        strs = ''
        for x in self.chars:
            if type(x).__name__ == 'str':
                strs += x
            else:
                strs += x.accessible(modus)
        return strs
        
class Environment(Element):
    def __init__(self, line, indent = -1):
        '''Create empty environment

        - "line" can be either a Line object or a string of the form:

          # instruction additional instructions

          e.g. # Lemma lma:label Name of lemma

          or # tikzpicture alt text

        - If "indent" is not specified then line.indent is
          the number of whitespace characters at the beginning of line

        - self.contents is initially empty and is populated by the taggify()
          function of the environment's parent.
        '''
        if type(line).__name__ == 'Line':
            self.indent = line.indent
            instruction = [''.join(c) for c in split_by_char(line.chars, ' ')]
        elif type(line).__name__ == 'str':
            self.indent = indent
            instruction = line.split()
        assert instruction[0] == '#'
        self.name = instruction[1]
        if len(instruction) > 2:
            self.additional = instruction[2:]
        else:
            self.additional = []
        self.contents = []

    def process(self):
        '''Apply various (non-recursive) processes to the elements of self.content
        and then recursively apply these processes to their children.'''
        if self.name == 'tikzpicture':
            # Don't touch this
            return None
        
        self.taggify()
        self.merge()
        self.equify()

        self.make_paragraphs() # Split Lines into Paragraphs
        self.group_list_items()

            
    def taggify(self):
        '''Converts Lines into Environments if appropriate

        Operates on self.contents.

        self.contents starts life empty, and is then populated by the
        taggify() function of self's parent; it becomes a list of Lines.
        self.taggify() goes through self.contents and replaces it by a new list:

        - if a line is of the form '# environment etc' and on the same
          indent level as self then a new environment is created and
          all subsequent lines of greater indentation are added to the
          contents of the new environment, until we return to
          self.indent level.

        - if a line is not of this form and is on the same indent
          level as self it is added back to self.contents without
          change.

        '''
        open_environment = None
        new_contents = []
        
        for line in self.contents:
            i = line.indent
            if open_environment:
                if i == None or i > open_environment.indent:
                    # Add blank lines or lines of greater indent to the open environment
                    open_environment.contents += [line]
                elif line.is_env():
                    # Create a new environment and update the open_environment
                    new_contents += [line.envify()]
                    open_environment = new_contents[-1]
                else:
                    # Just add line to the new self.contents
                    new_contents += [line]
                    open_environment = None
            elif i == None or not line.is_env():
                # If there's nothing open and the line is blank or not
                # a new environment just add it in to the new
                # self.contents
                new_contents += [line]
            else:
                # otherwise, create a new environment
                new_contents += [line.envify()]
                open_environment = new_contents[-1]
                
        self.contents = new_contents
        for x in self.contents:
            x.taggify()

    def merge(self):
        '''Operates on self.contents

        Goes through self.contents merging lines at the same indent level.
        Note that the indent level of all non-environment lines should be
        the same by this point in the process.

        '''
        if self.name == 'tikzpicture':
            # We don't want to merge tikzpictures
            return None
            
        merged = [self.contents.pop(0)]
        while self.contents:
            line = self.contents.pop(0)
            if type(line).__name__ == 'Environment':
                # Environments don't merge
                merged += [line]
            elif type(line).__name__ == 'Line':
                if type(merged[-1]).__name__ == 'Line':
                    # If previous line was not an environment then merge 
                    if line.is_empty():
                        merged[-1] += Line.empty_line()
                    else:
                        merged[-1] += line
                else:
                    # otherwise start a new line
                    merged += [line]

        self.contents = merged
        for x in self.contents:
            x.merge()
        
    def equify(self):
        '''Convert LaTeX into equations in any children.'''

        for line in self.contents:
            line.equify()

    def make_paragraphs(self):
        '''Operates on self.contents.

        Takes each Line object and splits it into paragraphs according
        to the appearance of parbreaks (inserted earlier by merge()).

        '''
        if self.name == 'tikzpicture':
            # Don't want to mess with the tikz
            return None
        
        paragraphed = []
        for line in self.contents:
            paragraphed += line.split_paragraphs()

        self.contents = paragraphed        
        for x in self.contents:
            x.make_paragraphs()
        
    def group_list_items(self):
        '''Operates on self.contents

        Goes through self.contents looking for contiguous groups of "uli" or "oli"
        (i.e. un-ordered or ordered list item environments). It groups these 
        together inside new "ul" or "ol" environments.

        '''
        in_list = 'none'
        new_contents = []

        for line in self.contents:
            if in_list == line.name:
                # If we're in a contiguous group of list-items of the same type
                # add this line to the currently open ul or ol environment,
                # which should be new_contents[-1]
                line.name = 'li'
                new_contents[-1].contents += [line]
            else:
                if line.name in ['uli', 'oli']:
                    # Starting a new contiguous group
                    in_list = line.name
                    list_type = line.name[0:2]
                    new_contents += [Environment('# ' + list_type)]
                    line.name = 'li'
                    new_contents[-1].contents += [line]
                else:
                    # Not a list-item
                    new_contents += [line]

        self.contents = new_contents
        
        for x in self.contents:
            x.group_list_items()
        
    def make_tikz(self):
        '''Generate image and img tag from tikzpicture Environment.

        We assume that # tikzpicture is of the form:

        # tikzpicture label

        or

        # tikzpicture label alt_text

        '''
        if len(self.additional) > 1:
            alt_text = ' '.join(self.additional[1:])
        else:
            alt_text = 'No alt text yet, sorry'
        label_text = str(self.additional[0])
        
        stump = img_path + str(self.additional[0])
        latex_tmp = stump + '.tex'
        jpg_file = stump
        pdf_tmp = str(self.additional[0]) + '.pdf'
        
        tikz_tmp = open(latex_tmp, "w")
        file_content = '\n'.join(['\\documentclass{standalone}',
                                  '\\usepackage{amsmath}',
                                  '\\usepackage{tikz}',
                                  '\\begin{document}',
                                  '\\begin{tikzpicture}'])
        file_content += '\n'.join([c.tikz_str() for c in self.contents])
        file_content += '\n'.join(['\\end{tikzpicture}',
                                  '\\end{document}'])
        
        tikz_tmp.write(file_content)
        tikz_tmp.close()
        run(["pdflatex",
             latex_tmp,
             "-output-directory="+img_path,
             pdf_tmp])
        run(["pdftocairo",
             "-singlefile",
             "-jpeg",
             pdf_tmp,
             jpg_file])

        img_tag = '\n'.join(['<figure>'
                             '<center>'
                             '<img src="' + jpg_file + '.jpg" alt="' + alt_text + '"/>',
                             '</center>',
                             '</figure>'])
        
        return img_tag
        

    def __str__(self):
        return self.__repr__()
    
    def __repr__(self):
        return self.accessible('mathml')
    
    def accessible(self, modus):
        if self.name in theorem_list:
            strs = ['<figure class="'+self.name+'">']
            if self.additional:
                id_label = self.additional[0]
                strs += ['<figcaption id="' + id_label + '">']
                if len(self.additional) > 1:
                    text_label = ' '.join(self.additional[1:])
                    strs += [self.name + ' (' + text_label + '): ']
                else:
                    strs += [self.name + ': ']
                strs += ['</figcaption>']
            else:
                strs += ['<figcaption>' + self.name + ': </figcaption>']
                
            strs += [c.accessible(modus) for c in self.contents]
            strs += ['</figure>']
        elif self.name == 'void':
            # This is a special kind of environment used for
            # the orphaned content of a section
            strs = [c.accessible(modus) for c in self.contents]
        elif self.name == 'tikzpicture':
            strs = [self.make_tikz()]
        else:
            strs = ['<'+self.name+'>']
            strs += [c.accessible(modus) for c in self.contents]
            strs += ['</'+self.name+'>']
        return '\n'.join(strs)

    
class Section:
    def __init__(self, line):
        '''Create an empty section

        The input is a line like:

        '* Introduction'

        or

        '** Subsection about some important topic'

        self.stars is 1 + the number of "subs" in front of "section".
        self.idnum is a randomly generated unique id for the section
        self.name is the name of the section
        self.contents is empty but will be filled with the contents
                      of the section when you run sectionise() on the
                      section of which this one is a subsection.
        self.orphaned_contents is empty but will be filled with any
                      content that is not part of a subsection by the
                      function self.sectionise().
        self.sections is empty but will be filled with a list of 
                      subsections by self.sectionise().
        '''
        self.idnum = str(random.random())[2:]
        self.stars = line.stars()
        self.name = ''.join(line.chars[self.stars+1:])
        self.contents = []
        self.orphaned_contents = []
        self.sections = []

    def sectionise(self):
        '''Populates subsections with contents and populates self.sections

        Each section (except Main) is populated with contents by the
        sectionise() function of its parent (i.e. the section to whose
        contents it belongs).

        self.sectionise() goes through the contents of a section
        "self", putting each line into a list called
        "self.orphaned_contents" until it finds a subsection (i.e. a
        line starting with stars that are not part of an equation). It
        then starts building up a list "self.sections" of subsections
        of depth 1 (i.e. 1 greater than self.stars), populating each
        one with subsequent lines. Note that a line starting a
        subsection of greater depth is just added to the most recently
        opened subsection of depth 1.

        The final act of this function is to run sectionise() on all
        the subsections of self (so it's effectively recursive).

        '''
        sections = []
        orphaned_contents = []
        orphan_mode = True

        for line in self.contents:
            if orphan_mode:
                if line.stars():
                    orphan_mode = False
                    sections += [Section(line)]
                else:
                    orphaned_contents += [line]
            elif line.stars() != self.stars + 1:
                sections[-1].contents += [line]
            else:
                sections += [Section(line)]

        self.orphaned_contents = orphaned_contents
        self.sections = sections
        
        for sct in self.sections:
            sct.sectionise()

    def taggify(self):
        '''Operates on self.orphaned_contents

        Puts all orphaned contents into a void environment for further
        processing. Then applies taggify to subsections.

        '''
        envelope = Environment('# void')
        envelope.contents = self.orphaned_contents
        envelope.process()
        self.orphaned_contents = [envelope]

        for sct in self.sections:
            sct.taggify()

    def __str__(self):
        return self.__repr__()
            
    def __repr__(self):
        return self.accessible('mathml')
        
    def accessible(self, modus):
        strs = ['<section id="s'+self.idnum+'" aria-labelledby="h'+self.idnum+'" role="region">']
        strs += ['<h'+str(self.stars+1)+' id="h'+self.idnum+'">'
                 +self.name
                 +'</h'+str(self.stars+1)+'>']
        strs += [c.accessible(modus) for c in self.orphaned_contents]
        strs += [c.accessible(modus) for c in self.sections]
        strs += ['</section>']
        return '\n'.join(strs)

    
class Main(Section):
    def __init__(self, contents, title):
        '''The main section of our document.

        '''
        self.contents = contents
        self.stars = 0
        self.name = 'main'
        self.title = title
        self.sections = []

        self.sectionise()

        for sct in self.sections:
            sct.taggify()

    def __str__(self):
        return self.__repr__()
            
    def __repr__(self):
        return self.accessible('mathml')
    
    def accessible(self, modus):
        strs = ['<main role="main">',
                '<header role="banner">',
                '<h1>' + self.title + '</h1>',
                '</header>']
        strs += [c.accessible(modus) for c in self.sections]
        strs += ['</main>']
        return '\n'.join(strs)    

    
class Document:
    def __init__(self, filename, mode = '\\('):
        self.mode = mode # '\(' or '$'
        with open(filename) as f:
            self.data = f.read()
            
        self.group_chars() # operates on self.data
        self.add_gaps()    # operates on self.data
        
        self.lines = [Line(x, y)
                      for x, y in zip(split_by_char(self.data, '\n'),
                                      split_by_char(self.get_eq_map(), '\n'))]
        
        self.run_commands()             # operates on self.lines
        self.create_list_environments() # operates on self.lines

        if not hasattr(self, 'title'):
            raise Exception("Accessible documents need a title. Use @ title in your input file.")
        self.main = Main(self.lines, self.title)

    def add_gaps(self):
        shifted_data = self.data[1:] + [' ']
        data_out = []
        skip_next_char = 0
        for x, y in zip(self.data, shifted_data):
            if skip_next_char == 0:
                if x == '\n' and y == '\n':
                    data_out += [x, ' ', y]
                    skip_next_char = 1
                else:
                    data_out += [x]
            else:
                skip_next_char = 0

        self.data = data_out
        
    def group_chars(self):
        '''Go through file and merge \(, $$, \$, etc into single characters.'''
        shifted_data = self.data[1:] + ' '
        data_out = []
        skip_next_char = 0
        for x, y in zip(self.data, shifted_data):
            if skip_next_char == 0:
                merge_test_1 = (x == '\\' and y in ['(', ')', '[', ']', '$'])
                merge_test_2 = (x == '$' and y == '$')
                if merge_test_1 or merge_test_2:
                    data_out += [x + y]
                    skip_next_char = 1
                else:
                    data_out += [x]
            else:
                skip_next_char = 0

        self.data = data_out

    def get_eq_map(self):
        eq_map = []
        in_eq = False
        if self.mode == '\\(':
            delimiters = ['\\[', '\\(', '\\]', '\\)', '$$']
        elif self.mode == '$':
            delimiters = ['\\[', '$', '\\]', '$$']
        for char in self.data:
            if char in delimiters:
                eq_map += [True]
                in_eq = not in_eq                    
            elif char == '\n':
                eq_map += ['\n']
            else:
                eq_map += [in_eq]

        return eq_map


    def run_commands(self):
        lines_to_remove = []
        line_counter = 0
        for line in self.lines:
            if line.chars[0] == '@':
                lines_to_remove += [line_counter]
                line_text = split_by_char(line.chars, ' ')
                command_name = ''.join(line_text[1])
                arguments = ' '.join([''.join(l) for l in line_text[2:]])
                if hasattr(self, command_name):
                    current = getattr(self, command_name)
                    setattr(self, command_name, ' '.join([current, arguments]))
                else:
                    setattr(self, command_name, arguments)
            line_counter += 1
            
        self.lines = [self.lines[i]
                      for i in range(0, len(self.lines))
                      if i not in lines_to_remove]
        
    def create_list_environments(self):
        new_lines = []
        new_map = []
        for line in self.lines:
            i = line.indent
            if i != None:
                if line.chars[i] == '-' and line.char_map[i] == False:
                    new_line_1 = line.chars[0:i] + ['#'] + [' '] + ['uli']
                    new_map_1 = [False for k in range(0, i+3)]
                    new_line_2 = line.chars[0:i] + [' '] + [' '] + line.chars[i + 2:]
                    new_map_2 = [False for k in range(0, i+2)] + line.char_map[i + 2:]
                    new_lines += [Line(new_line_1, new_map_1),
                                  Line(new_line_2, new_map_2)]
                elif line.chars[i] == '+' and line.char_map[i] == False:
                    new_line_1 = line.chars[0:i] + ['#'] + [' '] + ['oli']
                    new_map_1 = [False for k in range(0, i+3)]
                    new_line_2 = line.chars[0:i] + [' '] + [' '] + line.chars[i + 2:]
                    new_map_2 = [False for k in range(0, i+2)] + line.char_map[i + 2:]
                    new_lines += [Line(new_line_1, new_map_1),
                                  Line(new_line_2, new_map_2)]
                else:
                    new_lines += [line]
            else:
                new_lines += [line]

        self.lines = new_lines

    def get_meta(self, tag):
        if tag == 'title':
            if not hasattr(self, 'title'):
                raise Exception('Accessible documents need a title')
            else:
                return ['<title>',
                        getattr(self, tag),
                        '</title>']
        else:
            if hasattr(self, tag):
                return ['<meta name="'
                        + tag
                        + '" content="'
                        + getattr(self, tag) + '"/>']
            else:
                return []

    def get_external(self, what_to_get):
        if hasattr(self, what_to_get):
            external_filename = getattr(self, what_to_get)
            with open(external_filename, "r") as external_info:
                data = external_info.read()

            return [data]
        else:
            return []

    def get_nav(self, modus):
        if hasattr(self, 'nav'):
            external_filename = self.nav
            with open(external_filename, "r") as external_navfile:
                content_list = yaml.load(external_navfile, Loader=yaml.FullLoader)

            index_link = content_list['Index']
            notes_list = [x for y in content_list['Notes'] for x in y.keys()]
            notes_dict = {}
            for x in content_list['Notes']:
                notes_dict.update(x)
                
            current_node = notes_list.index(input_file[:-4])
            if current_node == 0:
                _prev = None
            else:
                _prev = notes_list[current_node - 1]
            if current_node == len(notes_list) - 1:
                _next = None
            else:
                _next = notes_list[current_node + 1]
            if modus == 'mathml':
                previous_link = str(_prev) + '.html'
                next_link = str(_next) + '.html'
            elif modus == 'alt':
                previous_link = str(_prev) + '_accessible.html'
                next_link = str(_next) + '_accessible.html'
            return_string = ['<nav role="navigation">', '<hr/>']
            if _prev:
                return_string += ['<a href="' + previous_link +'">Previous: ' + notes_dict[_prev] + '</a>']
            return_string += ['<a href="' + index_link + '">| Index of lectures</a>']
            if modus == 'mathml':
                return_string += ['<a href="' + output_accessible +'">| Replace MathML by alt-text in this page |</a>']
            elif modus == 'alt':
                return_string += ['<a href="' + output_mathml +'">| Reinstate MathML in this page |</a>']

            if _next:
                return_string += ['<a href="' + next_link +'">Next:' + notes_dict[_next] + '</a>']
            return_string += ['<hr/>', '</nav>']
            return return_string
        else:
            return []
                
    def __str__(self):
        return self.__repr__()
        
    def __repr__(self):
        return self.accessible('mathml')

    def accessible(self, modus):
        strs = ['<!DOCTYPE html>',
                '<html lang="en">',
                '<head>']
        for tag in meta_tags:
            strs += self.get_meta(tag)
        strs += self.get_external('headcontent')
        strs += ['</head>', '<body>']
        strs += self.get_nav(modus)
        #etc
        strs += [self.main.accessible(modus)]
        #etc
        strs += self.get_external('footer')
        strs += ['</body>', '</html>']
        return '\n'.join(strs)
        
if __name__ == '__main__':
    c = Document(input_file)
    out_1 = open(output_mathml, "w")
    out_2 = open(output_accessible, "w")
    out_1.write(c.accessible('mathml'))
    out_2.write(c.accessible('alt'))
    out_1.close()
    out_2.close()



