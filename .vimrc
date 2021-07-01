" vimrc created by alexander krabbe 

colorscheme dichromatic "colour blind colourscheme. normal: badwolf

" plugins for pluginstall
" call plug#begin('~/.vim/plugged')

"Plug 'itchyny/lightline.vim'

" call plug#end()


" Custom Silent command that will call redraw
command! -nargs=+ Silent
\   execute 'silent ! <args>'
\ | redraw!

" Easy compiling latex files from vim
":map <F5> :Silent pdflatex % && open -a Preview && open -a iTerm
":map <F6> :Silent pdflatex % && open -a zathura && open -a iTerm

" Python programming
" enable all Python syntax highlighting features
let python_highlight_all = 1
syntax on                     " syntax highlighing
filetype on                   " try to detect filetypes
filetype plugin indent on     " enable loading indent file for filetype
set number                    " Display line numbers
set numberwidth=1             " using only 1 column (and 1 space) while possible
set cursorline                " highlights current line for easier navigation
set background=dark           " We are using dark background in vim
set title                     " show title in console title bar
set wildmenu                  " Menu completion in command mode on <Tab>
set wildmode=full             " <Tab> cycles between all matching choices.
set showcmd
set scrolloff=7

set colorcolumn=105

set tabstop=4
set shiftwidth=4
set expandtab
set smarttab
set autoindent
set smartindent


set ruler

set hidden

set nolazyredraw
set showmatch
set encoding=utf8

""" Searching and Patterns
set ignorecase              " Default to using case insensitive searches,
set smartcase               " unless uppercase letters are used in the regex.
set smarttab                " Handle tabs more intelligently
set hlsearch                " Highlight searches by default.
set incsearch               " Incrementally search while typing a /regex

" Flash screen instead of beep sound
set visualbell

" Trying to include a new colour scheme for channel file for QMS channel list at dtu
au BufRead,BufNewFile *.txt set filetype=channel

" me copying a statusline from the interwebs: https://dustri.org/b/lightweight-and-sexy-status-bar-in-vim.html
set laststatus=2

set statusline=
set statusline+=%#DiffAdd#%{(mode()=='n')?'\ \ NORMAL\ ':''}
set statusline+=%#DiffChange#%{(mode()=='i')?'\ \ INSERT\ ':''}
set statusline+=%#DiffDelete#%{(mode()=='r')?'\ \ RPLACE\ ':''}
set statusline+=%#Cursor#%{(mode()=='v')?'\ \ VISUAL\ ':''}
set statusline+=\ %n\           " buffer number
set statusline+=%#Visual#       " colour
set statusline+=%{&paste?'\ PASTE\ ':''}
set statusline+=%{&spell?'\ SPELL\ ':''}
set statusline+=%#CursorIM#     " colour
set statusline+=%R                        " readonly flag
set statusline+=%M                        " modified [+] flag
set statusline+=%#Cursor#               " colour
set statusline+=%#CursorLine#     " colour
set statusline+=\ %t\                   " short file name
set statusline+=%=                          " right align
set statusline+=%#CursorLine#   " colour
set statusline+=\ %Y\                   " file type
set statusline+=%#CursorIM#     " colour
set statusline+=\ %3l:%-2c\         " line + column
set statusline+=%#Cursor#       " colour
set statusline+=\ %3p%%\                " percentage
