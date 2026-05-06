// Inline article comments. Reader drops a paragraph-anchored
// note; it's stored as a sibling JSON file next to the essay:
//
//	foo.md  →  foo.md.comments.json
//
// No database, no auth. Author comes from a form field (or
// defaults to "reader"). Comments are append-only via the UI;
// manual edits to the sibling JSON are fine.
package main

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type articleComment struct {
	ParaIndex int    `json:"para_index"`
	Author    string `json:"author"`
	Timestamp string `json:"timestamp"`
	Text      string `json:"text"`
}

type articleCommentFile struct {
	Comments []articleComment `json:"comments"`
}

// resolveArticlePath accepts the full URL path of an essay
// and returns the filesystem path, refusing traversal
// attempts. Five shapes:
//
//	/essays/<name>.md
//	/claude-claude/<name>.md
//	/users/steve/<subdir>/<name>.md
//	/steve/<name>.md
//	/steve/<subdir>/<name>.md
func resolveArticlePath(article string) (string, bool) {
	var dir, name string
	switch {
	case strings.HasPrefix(article, "/essays/"):
		dir = EssaysDir
		name = strings.TrimPrefix(article, "/essays/")
	case strings.HasPrefix(article, "/claude-claude/"):
		dir = ClaudeClaudeDir
		name = strings.TrimPrefix(article, "/claude-claude/")
	case strings.HasPrefix(article, "/steve/"):
		rest := strings.TrimPrefix(article, "/steve/")
		parts := strings.SplitN(rest, "/", 2)
		if len(parts) == 1 {
			dir = SteveRootDir
			name = parts[0]
		} else {
			subdir := parts[0]
			if !isValidSteveSubdir(subdir) {
				return "", false
			}
			dir = filepath.Join(SteveRootDir, subdir)
			name = parts[1]
		}
	case strings.HasPrefix(article, "/users/steve/"):
		rest := strings.TrimPrefix(article, "/users/steve/")
		parts := strings.SplitN(rest, "/", 2)
		if len(parts) != 2 {
			return "", false
		}
		subdir := parts[0]
		if !isValidSteveSubdir(subdir) {
			return "", false
		}
		dir = filepath.Join(SteveBaseDir, subdir)
		name = parts[1]
	default:
		return "", false
	}
	if strings.Contains(name, "..") || strings.Contains(name, "/") {
		return "", false
	}
	if !strings.HasSuffix(name, ".md") {
		return "", false
	}
	return filepath.Join(dir, name), true
}

func commentsSidecarPath(articleAbs string) string {
	return articleAbs + ".comments.json"
}

func loadArticleComments(articleAbs string) articleCommentFile {
	data, err := os.ReadFile(commentsSidecarPath(articleAbs))
	if err != nil {
		return articleCommentFile{}
	}
	var f articleCommentFile
	if err := json.Unmarshal(data, &f); err != nil {
		return articleCommentFile{}
	}
	return f
}

func saveArticleComments(articleAbs string, f articleCommentFile) error {
	data, err := json.MarshalIndent(f, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(commentsSidecarPath(articleAbs), data, 0644)
}

func HandleArticleComments(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method == "GET" {
		article := r.URL.Query().Get("article")
		abs, ok := resolveArticlePath(article)
		if !ok {
			http.Error(w, `{"error":"invalid article path"}`, http.StatusBadRequest)
			return
		}
		f := loadArticleComments(abs)
		_ = json.NewEncoder(w).Encode(f)
		return
	}
	if r.Method != "POST" {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}
	if err := r.ParseForm(); err != nil {
		http.Error(w, `{"error":"bad form"}`, http.StatusBadRequest)
		return
	}
	article := r.FormValue("article")
	abs, ok := resolveArticlePath(article)
	if !ok {
		http.Error(w, `{"error":"invalid article path"}`, http.StatusBadRequest)
		return
	}
	paraIdx, _ := strconv.Atoi(r.FormValue("para_index"))
	text := strings.TrimSpace(r.FormValue("text"))
	if text == "" {
		http.Error(w, `{"error":"empty comment"}`, http.StatusBadRequest)
		return
	}
	author := strings.TrimSpace(r.FormValue("author"))
	if author == "" {
		author = "reader"
	}
	f := loadArticleComments(abs)
	f.Comments = append(f.Comments, articleComment{
		ParaIndex: paraIdx,
		Author:    author,
		Timestamp: time.Now().Format(time.RFC3339),
		Text:      text,
	})
	if err := saveArticleComments(abs, f); err != nil {
		http.Error(w, `{"error":"cannot save: `+err.Error()+`"}`, http.StatusInternalServerError)
		return
	}
	_ = json.NewEncoder(w).Encode(f)
}

// ArticleCommentsJS is the client-side script injected into
// rendered markdown. It walks each paragraph inside .wiki-md,
// renders any existing comments beneath it, and adds a "note"
// button that opens a compose box.
const ArticleCommentsJS = `
<script>
(function(){
  var container = document.querySelector('.wiki-md');
  if (!container) return;

  // Use the full URL path as the article identifier. Server
  // dispatches on the known prefixes (/essays/, /users/steve/general/).
  if (!/\.md$/.test(location.pathname)) return;
  var articlePath = location.pathname;

  var style = document.createElement('style');
  style.textContent = [
    '.para-wrap { position: relative; }',
    '.para-add-btn { margin-left: 8px; cursor: pointer; font-size: 13px; border: 1px solid #000080; background: white; color: #000080; padding: 1px 6px; border-radius: 3px; vertical-align: middle; }',
    '.para-add-btn:hover { background: #000080; color: white; }',
    '.para-comments { margin: 6px 0 14px 24px; padding-left: 10px; border-left: 3px solid #d6d0be; }',
    '.para-comment { background: #faf7ef; border: 1px solid #e8e1cc; border-radius: 3px; padding: 10px 12px; margin: 6px 0; font-size: 14px; font-family: sans-serif; color: #333; line-height: 1.55; }',
    '.para-comment .meta { color: #888; font-size: 11px; margin-bottom: 2px; }',
    '.para-compose { margin: 6px 0 14px 24px; padding: 8px; background: #fff3a8; border: 1px solid #e6d670; border-radius: 4px; font-family: sans-serif; }',
    '.para-compose input.author { width: 180px; padding: 4px 8px; font-size: 13px; margin-bottom: 6px; border: 1px solid #c9bfa7; border-radius: 3px; }',
    '.para-compose textarea { width: 100%; min-height: 120px; padding: 8px 10px; font-size: 14px; font-family: sans-serif; line-height: 1.5; box-sizing: border-box; border: 1px solid #c9bfa7; border-radius: 3px; }',
    '.para-compose button { margin-top: 6px; margin-right: 6px; padding: 4px 12px; font-size: 13px; border: none; border-radius: 3px; cursor: pointer; }',
    '.para-compose .save { background: #000080; color: white; }',
    '.para-compose .cancel { background: #eee; color: #333; }',
  ].join('\n');
  document.head.appendChild(style);

  // Candidates: paragraphs + list items. Skip <li>s that
  // already contain a <p> (loose lists) so we don't double-
  // count — the inner <p> gets the button instead.
  var candidates = container.querySelectorAll('p, li');
  var paras = [];
  candidates.forEach(function(el){
    if (el.tagName === 'LI' && el.querySelector(':scope > p')) return;
    paras.push(el);
  });
  var paraByIndex = {};
  paras.forEach(function(p, i){
    p.setAttribute('data-para-index', i);
    p.classList.add('para-wrap');
    paraByIndex[i] = p;

    var btn = document.createElement('button');
    btn.className = 'para-add-btn';
    btn.textContent = 'note';
    btn.title = 'Add a note on this paragraph';
    btn.addEventListener('click', function(){ openCompose(i); });
    p.appendChild(btn);
  });

  function attachAfter(p, child) {
    if (p.tagName === 'LI') p.appendChild(child);
    else p.parentNode.insertBefore(child, p.nextSibling);
  }
  function findExistingCommentsBox(p) {
    if (p.tagName === 'LI') return p.querySelector(':scope > .para-comments');
    var sib = p.nextElementSibling;
    if (sib && sib.classList.contains('para-comments')) return sib;
    return null;
  }

  fetch('/article-comments?article=' + encodeURIComponent(articlePath))
    .then(function(r){ return r.ok ? r.json() : { comments: [] }; })
    .then(function(data){ (data.comments || []).forEach(renderComment); });

  function renderComment(c) {
    var p = paraByIndex[c.para_index];
    if (!p) return;
    var box = findExistingCommentsBox(p);
    if (!box) {
      box = document.createElement('div');
      box.className = 'para-comments';
      box.setAttribute('data-para-index', c.para_index);
      attachAfter(p, box);
    }
    var cEl = document.createElement('div');
    cEl.className = 'para-comment';
    var meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = c.author + ' · ' + c.timestamp;
    cEl.appendChild(meta);
    var text = document.createElement('div');
    text.textContent = c.text;
    cEl.appendChild(text);
    box.appendChild(cEl);
  }

  function openCompose(paraIdx) {
    var existing = document.querySelector('.para-compose[data-para-index="' + paraIdx + '"]');
    if (existing) { existing.querySelector('textarea').focus(); return; }

    var p = paraByIndex[paraIdx];
    var compose = document.createElement('div');
    compose.className = 'para-compose';
    compose.setAttribute('data-para-index', paraIdx);
    compose.innerHTML =
      '<div><input type="text" class="author" placeholder="your name" value="' + (localStorage.getItem('claudeCollabAuthor') || '') + '"></div>' +
      '<textarea placeholder="Light note..."></textarea>' +
      '<div><button class="save">Save</button><button class="cancel">Cancel</button></div>';

    var existingBox = findExistingCommentsBox(p);
    if (existingBox) existingBox.parentNode.insertBefore(compose, existingBox.nextSibling);
    else attachAfter(p, compose);

    var textarea = compose.querySelector('textarea');
    textarea.focus();

    compose.querySelector('.cancel').addEventListener('click', function(){ compose.remove(); });
    compose.querySelector('.save').addEventListener('click', function(){
      var text = textarea.value.trim();
      if (!text) return;
      var author = (compose.querySelector('input.author').value || 'reader').trim();
      try { localStorage.setItem('claudeCollabAuthor', author); } catch(_){}
      var body = new URLSearchParams();
      body.set('article', articlePath);
      body.set('para_index', String(paraIdx));
      body.set('text', text);
      body.set('author', author);
      fetch('/article-comments', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: body.toString(),
      }).then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function(data){
          document.querySelectorAll('.para-comments').forEach(function(el){ el.remove(); });
          (data.comments || []).forEach(renderComment);
          compose.remove();
        })
        .catch(function(err){ alert('Failed to save: ' + err); });
    });
  }
})();
</script>
`
