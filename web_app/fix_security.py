#!/usr/bin/env python3
"""
安全修复脚本
修复以下安全问题：
1. 路径遍历漏洞 - 静态文件服务
2. Cookie安全标志 - Secure, HttpOnly, SameSite
3. CSRF保护增强
4. 输入验证增强
5. 安全响应头
"""
import os
import re


def fix_path_traversal_vulnerability():
    """修复静态文件服务的路径遍历漏洞"""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_static_handling = """        elif path.startswith("/static/assets/"):
            # Serve payment QR code images
            asset_path = os.path.join(os.path.dirname(__file__), path[1:])
            if os.path.exists(asset_path):"""
    
    new_static_handling = """        elif path.startswith("/static/assets/"):
            # Serve payment QR code images (path traversal protection)
            safe_path = os.path.normpath(path[1:])
            if '..' in safe_path.split(os.sep) or not safe_path.startswith('static' + os.sep + 'assets' + os.sep):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            asset_path = os.path.join(os.path.dirname(__file__), safe_path)
            asset_dir = os.path.join(os.path.dirname(__file__), 'static', 'assets')
            try:
                real_asset = os.path.realpath(asset_path)
                real_dir = os.path.realpath(asset_dir)
                if not real_asset.startswith(real_dir + os.sep) and real_asset != real_dir:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden")
                    return
            except Exception:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            if os.path.exists(asset_path) and os.path.isfile(asset_path):"""
    
    if old_static_handling in content:
        content = content.replace(old_static_handling, new_static_handling)
        print("  [FIXED] 路径遍历漏洞 - 静态文件服务")
    else:
        print("  [SKIP] 路径遍历漏洞已修复或代码结构已变更")
    
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def fix_cookie_security():
    """修复Cookie安全标志"""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_cookie1 = 'self.send_header("Set-Cookie", f"session={cookie_token}; Path=/; Max-Age=2592000")'
    new_cookie1 = 'self.send_header("Set-Cookie", f"session={cookie_token}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax")'
    
    old_cookie2 = 'self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")'
    new_cookie2 = 'self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")'
    
    changes = 0
    if old_cookie1 in content:
        content = content.replace(old_cookie1, new_cookie1)
        changes += 1
        print("  [FIXED] Cookie安全标志 - 登录Cookie添加HttpOnly和SameSite")
    
    if old_cookie2 in content:
        content = content.replace(old_cookie2, new_cookie2)
        changes += 1
        print("  [FIXED] Cookie安全标志 - 登出Cookie添加HttpOnly和SameSite")
    
    if changes == 0:
        print("  [SKIP] Cookie安全标志已修复或代码结构已变更")
    
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def add_security_headers():
    """添加安全响应头"""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_send_html = """    def send_html(self, html_content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode())"""
    
    new_send_html = """    def send_html(self, html_content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        self.end_headers()
        self.wfile.write(html_content.encode())"""
    
    if old_send_html in content:
        content = content.replace(old_send_html, new_send_html)
        print("  [FIXED] 安全响应头 - 添加X-Content-Type-Options, X-Frame-Options, X-XSS-Protection等")
    else:
        print("  [SKIP] 安全响应头已修复或代码结构已变更")
    
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def enhance_input_validation():
    """增强输入验证"""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_match_handling = """        elif path.startswith("/match/"):
            parts = path.split("/")
            if len(parts) >= 4:
                home_name = urllib.parse.unquote(parts[2])
                away_name = urllib.parse.unquote(parts[3])
                html = handle_match_detail(token, home_name, away_name)
                self.send_html(html)
            else:
                self.send_redirect("/matches")"""
    
    new_match_handling = """        elif path.startswith("/match/"):
            parts = path.split("/")
            if len(parts) >= 4:
                home_name = urllib.parse.unquote(parts[2])
                away_name = urllib.parse.unquote(parts[3])
                if not re.match(r'^[\\w\\s\\-&]+$', home_name) or not re.match(r'^[\\w\\s\\-&]+$', away_name):
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("<h1>400 Bad Request</h1><p>无效的球队名称。</p>".encode())
                    return
                html = handle_match_detail(token, home_name, away_name)
                self.send_html(html)
            else:
                self.send_redirect("/matches")"""
    
    old_report_handling = """        elif path.startswith("/report/"):
            parts = path.split("/")
            if len(parts) >= 4:
                home_name = urllib.parse.unquote(parts[2])
                away_name = urllib.parse.unquote(parts[3])
                html = handle_report(token, home_name, away_name)
                self.send_html(html)
            else:
                self.send_redirect("/")"""
    
    new_report_handling = """        elif path.startswith("/report/"):
            parts = path.split("/")
            if len(parts) >= 4:
                home_name = urllib.parse.unquote(parts[2])
                away_name = urllib.parse.unquote(parts[3])
                if not re.match(r'^[\\w\\s\\-&]+$', home_name) or not re.match(r'^[\\w\\s\\-&]+$', away_name):
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("<h1>400 Bad Request</h1><p>无效的球队名称。</p>".encode())
                    return
                html = handle_report(token, home_name, away_name)
                self.send_html(html)
            else:
                self.send_redirect("/")"""
    
    changes = 0
    if old_match_handling in content:
        content = content.replace(old_match_handling, new_match_handling)
        changes += 1
        print("  [FIXED] 输入验证 - match路径参数验证")
    
    if old_report_handling in content:
        content = content.replace(old_report_handling, new_report_handling)
        changes += 1
        print("  [FIXED] 输入验证 - report路径参数验证")
    
    if changes == 0:
        print("  [SKIP] 输入验证已修复或代码结构已变更")
    
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def fix_admin_csrf_protection():
    """为管理员操作添加CSRF保护"""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_admin_result = """        elif path == "/api/admin/result":
            username = get_session_user(token)
            premium, ptype, reason = check_premium(token)
            if not premium or ptype != "all":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            params = urllib.parse.parse_qs(body)"""
    
    new_admin_result = """        elif path == "/api/admin/result":
            username = get_session_user(token)
            premium, ptype, reason = check_premium(token)
            if not premium or ptype != "all":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            params = urllib.parse.parse_qs(body)
            csrf_token = params.get("csrf_token", [""])[0]
            if not validate_csrf_token(csrf_token, token):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"CSRF token invalid or expired")
                return"""
    
    old_admin_refresh = """        elif path == "/api/admin/refresh":
            username = get_session_user(token)
            premium, ptype, reason = check_premium(token)
            if not premium or ptype != "all":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return"""
    
    new_admin_refresh = """        elif path == "/api/admin/refresh":
            username = get_session_user(token)
            premium, ptype, reason = check_premium(token)
            if not premium or ptype != "all":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else ""
            params = urllib.parse.parse_qs(body)
            csrf_token = params.get("csrf_token", [""])[0]
            if not validate_csrf_token(csrf_token, token):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"CSRF token invalid or expired")
                return"""
    
    old_admin_grant = """        elif path == "/api/admin/grant_premium":
            username = get_session_user(token)
            premium, ptype, reason = check_premium(token)
            if not premium or ptype != "all":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            params = urllib.parse.parse_qs(body)"""
    
    new_admin_grant = """        elif path == "/api/admin/grant_premium":
            username = get_session_user(token)
            premium, ptype, reason = check_premium(token)
            if not premium or ptype != "all":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            params = urllib.parse.parse_qs(body)
            csrf_token = params.get("csrf_token", [""])[0]
            if not validate_csrf_token(csrf_token, token):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"CSRF token invalid or expired")
                return"""
    
    changes = 0
    if old_admin_result in content:
        content = content.replace(old_admin_result, new_admin_result)
        changes += 1
        print("  [FIXED] CSRF保护 - /api/admin/result")
    
    if old_admin_refresh in content:
        content = content.replace(old_admin_refresh, new_admin_refresh)
        changes += 1
        print("  [FIXED] CSRF保护 - /api/admin/refresh")
    
    if old_admin_grant in content:
        content = content.replace(old_admin_grant, new_admin_grant)
        changes += 1
        print("  [FIXED] CSRF保护 - /api/admin/grant_premium")
    
    if changes == 0:
        print("  [SKIP] CSRF保护已修复或代码结构已变更")
    
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def add_csrf_tokens_to_admin_forms():
    """在管理员表单中添加CSRF token"""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    csrf_generation = """        if username == "admin":
            csrf_token = generate_csrf_token(token)
            csrf_field = f'<input type="hidden" name="csrf_token" value="{csrf_token}">'
        else:
            csrf_field = """""
    
    old_handle_admin_start = """def handle_admin(token):
    \"\"\"Admin dashboard - only for admin user.\"\"\"
    username = get_session_user(token)
    premium, ptype, reason = check_premium(token)
    if not premium or ptype != "all" or username != "admin":
        return "HTTP/1.0 403 Forbidden\\r\\nContent-Type: text/html\\r\\n\\r\\n<h1>403 Forbidden</h1>"
    users = load_json(USERS_FILE)"""
    
    new_handle_admin_start = """def handle_admin(token):
    \"\"\"Admin dashboard - only for admin user.\"\"\"
    username = get_session_user(token)
    premium, ptype, reason = check_premium(token)
    if not premium or ptype != "all" or username != "admin":
        return "HTTP/1.0 403 Forbidden\\r\\nContent-Type: text/html\\r\\n\\r\\n<h1>403 Forbidden</h1>"
    csrf_token = generate_csrf_token(token)
    users = load_json(USERS_FILE)"""
    
    if old_handle_admin_start in content:
        content = content.replace(old_handle_admin_start, new_handle_admin_start)
        print("  [FIXED] Admin CSRF - token生成")
    else:
        print("  [SKIP] Admin CSRF token生成已存在或代码结构已变更")
    
    old_form1 = """<form method="POST" action="/api/admin/result">"""
    new_form1 = f"""<form method="POST" action="/api/admin/result">
                    <input type="hidden" name="csrf_token" value="{{csrf_token}}">"""
    
    old_form2 = """<form method="POST" action="/api/admin/grant_premium">"""
    new_form2 = f"""<form method="POST" action="/api/admin/grant_premium">
                <input type="hidden" name="csrf_token" value="{{csrf_token}}">"""
    
    old_form3 = """<form method="POST" action="/api/admin/refresh">"""
    new_form3 = f"""<form method="POST" action="/api/admin/refresh">
            <input type="hidden" name="csrf_token" value="{{csrf_token}}">"""
    
    if old_form1 in content:
        content = content.replace(old_form1, new_form1)
        print("  [FIXED] Admin表单 - result表单添加CSRF token")
    
    if old_form2 in content:
        content = content.replace(old_form2, new_form2)
        print("  [FIXED] Admin表单 - grant_premium表单添加CSRF token")
    
    if old_form3 in content:
        content = content.replace(old_form3, new_form3)
        print("  [FIXED] Admin表单 - refresh表单添加CSRF token")
    
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def main():
    print("=" * 60)
    print("波胆教父 - 安全修复脚本")
    print("=" * 60)
    print()
    
    fixes = [
        ("路径遍历漏洞修复", fix_path_traversal_vulnerability),
        ("Cookie安全标志", fix_cookie_security),
        ("安全响应头", add_security_headers),
        ("输入验证增强", enhance_input_validation),
        ("CSRF保护增强", fix_admin_csrf_protection),
        ("Admin表单CSRF token", add_csrf_tokens_to_admin_forms),
    ]
    
    success_count = 0
    for name, fix_func in fixes:
        print(f"[{name}]")
        try:
            if fix_func():
                success_count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()
    
    print("=" * 60)
    print(f"安全修复完成: {success_count}/{len(fixes)} 项修复应用")
    print("=" * 60)
    print()
    print("建议: 重启服务器以应用所有修复")
    print("命令: python server.py")


if __name__ == "__main__":
    main()
