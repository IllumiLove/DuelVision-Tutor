"""QSS styles for the overlay window."""

OVERLAY_QSS = """
QWidget#overlay {
    background-color: rgb(20, 22, 40);
    border: 2px solid rgba(120, 140, 255, 120);
    border-radius: 10px;
}

QWidget {
    background-color: rgb(20, 22, 40);
}

QLabel#title {
    color: #A0B0FF;
    font-size: 16px;
    font-weight: bold;
    font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
    padding: 4px 8px;
}

QLabel#priority {
    color: #00FF88;
    font-size: 17px;
    font-weight: bold;
    font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
    padding: 8px 12px;
    background-color: rgba(0, 255, 136, 25);
    border: 1px solid rgba(0, 255, 136, 60);
    border-radius: 6px;
    margin: 4px 8px;
}

QLabel#step {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
    padding: 3px 12px;
    line-height: 1.5;
}

QLabel#reason {
    color: #C0C0C0;
    font-size: 13px;
    font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
    padding: 0px 20px 4px 20px;
}

QLabel#warning {
    color: #FFD700;
    font-size: 13px;
    font-weight: bold;
    font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
    padding: 3px 12px;
    background-color: rgba(255, 215, 0, 15);
    border-radius: 4px;
    margin: 2px 8px;
}

QLabel#assessment {
    color: #A0B0FF;
    font-size: 13px;
    font-family: "Microsoft JhengHei", "Segoe UI", sans-serif;
    padding: 6px 12px;
    border-top: 1px solid rgba(120, 140, 255, 60);
    margin-top: 4px;
}

QLabel#status {
    color: #888888;
    font-size: 11px;
    font-family: "Consolas", monospace;
    padding: 2px 8px;
    border-top: 1px solid rgba(120, 140, 255, 40);
}
"""
