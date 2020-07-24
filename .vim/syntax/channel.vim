" Vim syntax file
" Language: homemade colourscheme for channel_list used in mass_spec programs at surfcat
" Maintainer: Alexander Krabbe
" Latest revised 19I06

if exists("b:current_syntax")
    finish
endif

" Keywords
syn keyword celBlockCmd port amp_range mass speed masslabel repeat_interval label host command

syn keyword TitelBlock autorange comment ms_channel meta_channel

" syn keyword outcomment #

syn keyword celTodo contained TODO FIXME XXX NOTE

" Matches

syn match celComment "^#.*$" contains=celTodo

" Regions

let b:current_syntax = "channel"
hi def link celBlockCmd Constant
hi def link TitelBlock Statement
" Statement
hi def link celComment Comment
" hi def link outcomment Constant

