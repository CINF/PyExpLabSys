;; .emacs

(add-to-list 'load-path "~/.emacs.d/lisp/")

(require 'flymake)

(when (load "flymake" t)
  (defun flymake-pyflakes-init ()
    (let* ((temp-file (flymake-init-create-temp-buffer-copy
               'flymake-create-temp-inplace))
       (local-file (file-relative-name
            temp-file
            (file-name-directory buffer-file-name))))
      (list "pycheckers"  (list local-file))))
   (add-to-list 'flymake-allowed-file-name-masks
             '("\\.py\\'" flymake-pyflakes-init)))

(require 'flymake-cursor)

;;(add-hook 'python-mode-hook 'flymake-mode)
(global-set-key (kbd "<f5>") 'flymake-start-syntax-check)
(global-set-key (kbd "<f6>") 'flymake-display-err-menu-for-current-line)

;; enable visual feedback on selections
(setq transient-mark-mode t)
(setq column-number-mode t)

;; default to better frame titles
(setq frame-title-format
      (concat  "%b - emacs@" (system-name)))

;; default to unified diffs
(setq diff-switches "-u")
