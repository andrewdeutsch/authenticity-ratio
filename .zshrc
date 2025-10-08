if which rbenv > /dev/null; then eval "$(rbenv init -)"; fi
export 
PATH="/Users/andrewdeutsch/.gem/ruby/2.6.0/bin:$PATH"
# >>> alias python=/usr/bin/python3 >>>
# >>> alias python=/usr/bin/python3 >>>
if which rbenv > /dev/null; then eval "$(rbenv init -)"; fi
alias adb='/Users/$USER/Library/Android/sdk/platform-tools/adb'

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/opt/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

