#!/bin/bash
# tmux layout for mainframe automation demo
# Usage: tmux source-file demo.tmux

# Create session
tmux new-session -d -s mainframe -n demo

# Split window into 4 panes
# +-------------------+-------------------+
# | 0: Hercules       | 1: Bridge API     |
# |                   |                   |
# +-------------------+-------------------+
# | 2: Agent          | 3: Metrics        |
# |                   |                   |
# +-------------------+-------------------+

# Start Hercules console in pane 0
tmux send-keys -t mainframe:demo.0 'cd ~/herc/mvs38j/mvs-tk5 && tail -f ~/herc/logs/hercules.log' C-m

# Start Bridge API monitor in pane 1
tmux split-window -h -t mainframe:demo
tmux send-keys -t mainframe:demo.1 'watch -n 2 "curl -s http://127.0.0.1:8080/healthz | python3 -m json.tool"' C-m

# Start Agent in pane 2
tmux split-window -v -t mainframe:demo.0
tmux send-keys -t mainframe:demo.2 'cd ~/herc/ai && python run_agent.py --interactive' C-m

# Start metrics monitor in pane 3
tmux split-window -v -t mainframe:demo.1
tmux send-keys -t mainframe:demo.3 'watch -n 5 "cat ~/herc/logs/ai/metrics.json | python3 -m json.tool | tail -20"' C-m

# Set pane titles
tmux select-pane -t mainframe:demo.0 -T "Hercules Console"
tmux select-pane -t mainframe:demo.1 -T "Bridge Health"
tmux select-pane -t mainframe:demo.2 -T "AI Agent"
tmux select-pane -t mainframe:demo.3 -T "Metrics"

# Enable pane borders and titles
tmux set-option -t mainframe -g pane-border-status top
tmux set-option -t mainframe -g pane-border-format "#{pane_index}: #{pane_title}"

# Set active pane to Agent
tmux select-pane -t mainframe:demo.2

# Attach to session
tmux attach-session -t mainframe