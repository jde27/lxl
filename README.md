lxl - lazy accessible LaTeX
---------------------------

This is a Python script which takes a specially marked-up .lxl file
and turns it into:

- an HTML page with MathML equations.
- an HTML page where the MathML is replaced by alt text which you'd
  like your listener to hear.

The lxl file is just a text file containing text marked up in the
manner I will describe in the next few sections. To see a worked
example (as well as the auxiliary files) see the ``./example```
folder.

Todo: I still want to add stuff to the header which allows video
embedding.

Sections
========

```
* Section name

This is an interesting section

** Subsection
** Another subsection
*** A subsubsection
*** You get the idea
```

Indentation
===========

All grouping below the level of section/subsections is handled by
indentation. For example

```
# Theorem
  This is inside the theorem statement.
This isn't.
- This is inside a list
  and this list item runs over several lines
  - Now we're inside a sublist
    also with multiple lines
  - still in the sublist
- back in the list
out of the list
```

I recommend using a 2 space indent, but variable indent should also
work (as long as it makes sense), for example:

```
# Theorem
     Here is the statement
     - and a list
       - with a sublist
           - and a subsublist
             here
         continuing the sublist item
       - new sublist item
     Back to the theorem
Back to the main text
```

Lists
=====

```
- An
- unordered
- list

+ An
+ ordered
+ list
```

Environments
============

```
# Theorem thm:gauss Gauss's Theorem
  Wonderful facts, including
  - A
  - B
  - and C
```

So far I've included Lemma, Theorem, Remark, Corollary, Proposition,
Definition, Example, Proof. You can add more by editing the variable
```theorem_list``` in ```lxl.py```.

Meta-data
=========

```
@ title Document title
@ author Me
@ description Stuff that's used by search engines
@ description to figure out what you're site's all about
@ nav filename1
@ headcontent filename2
@ footer filename3
```

The only mandatory line one is title.

Here:
- ```filename1``` is a yaml file detailing the structure of your
  lecture notes. See ```./examples/outline.yaml``` for an example.
- ```filename2``` will be inserted verbatim into the head of your HTML
  document. This is where things like MathJax script tags need to go.
- ```filename3``` will be inserted verbatim into the footer of your
  HTML document. This is for an HTML footer tag containing
  e.g. copyright information.

TikZ
=========================

```
# tikzpicture pic_1 A blob
  \node at (0,0) {\(\bullet\)};
  \draw (0,0) -- (0,1);
```

will produce an image file called ```pic_1.jpg``` with alt text "a
blob". Both filename and alt text are mandatory. All lines inside the
tikzpicture should have the same indent and no lines should break.

Equations
=========
You can enter LaTeX as usual, e.g.

```
Here's an equation \(a+b=c\)
```

or 

```
Here's an equation $a+b=c$
```

if you prefer. Just be consistent and don't mix \( with $ delimiters.

Alt-text for equations
======================

This is the main innovation and it's optional. The alt text must be
entered into equations manually, e.g.

```
\(\frac{-b\pm\sqrt{b^2-4ac}}{2a}$minus b plus or minus
square root of b squared minus 4 a c, all over 2a$\)
```

In other words, you use your favourite delimiters (i.e. \(,\) or $,$)
around your equations, and then at the end (just before you close the
delimiters) you insert your alt text between another pair of
delimiters (of the opposite type). If you're using \[,\] or $$,$$
that's also fine: e.g. \[A^2$A squared$\] or \[A^2\(A squared\)\] will
work; $$A^2\(A squared\)$$ will work but $$A^2$A squared$$$ won't.

If you omit the alt text then default alt text will be used: your
LaTeX source code. This is so you don't have to use alt text for basic
things like \(x\) or \(\exp(A)\) (because the LaTeX is close enough to
what you'd say out loud that it doesn't matter).

