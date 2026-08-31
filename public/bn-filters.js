/**
 * بُنيان — وحدة الفلاتر وقائمة الشركات المشتركة
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٢ §٣ §٥·٥ §٦
 *
 * سبب وجودها: نسختان من منطق الفلترة تفترقان حتماً، فيُصلَح كل
 * عطب مرتين — ويُنسى مرة. هذه هي النسخة الوحيدة، وتستعملها
 * index.html و companies.html معاً.
 *
 * تحتوي:
 *   · حالة الفلتر (مدينة · تخصص · بحث) ومزامنتها مع عنوان URL
 *   · صفّ المدن المستقل وشرائح التخصص بأسهم وتلاشٍ
 *   · العدّادات المتقاطعة — عدّاد المدينة يحترم التخصص والعكس
 *   · الجلب من /companies بمعاملات الفلتر وترقيم الصفحات
 *   · صفوف الشركات الغنية، وحالتَي الفراغ والخطأ (مميّزتان)
 *
 * الاستعمال:
 *   const F = BunyanFilters.create({ onResults, perPage });
 *   F.init();
 */
(function () {
  'use strict';

  /* ── الأيقونات — SVG ترث currentColor، لا إيموجي (§٥·٥) ── */
  var IC = {
    pin:      '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    star:     '<path d="M12 3.7l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z"/>',
    check:    '<path d="M20 6L9 17l-5-5"/>',
    wa:       '<path d="M21 11.5a8.4 8.4 0 0 1-12.3 7.5L3.5 20.5l1.6-5A8.5 8.5 0 1 1 21 11.5z"/><path d="M8.9 8.4c.2-.5.4-.5.6-.5h.5c.2 0 .4 0 .6.5l.7 1.6c.1.2 0 .4-.1.5l-.4.5c-.1.2-.2.3-.1.5a5 5 0 0 0 2.3 2.2c.2.1.4.1.5-.1l.4-.5c.2-.2.3-.2.5-.1l1.6.8c.2.1.3.2.3.4a1.6 1.6 0 0 1-1.1 1.3c-.4.1-1 .2-2.6-.5a8.6 8.6 0 0 1-3.6-3.4c-.6-1.1-.6-1.8-.5-2.2a1.8 1.8 0 0 1 .4-1z"/>',
    chevS:    '<path d="M15 6l-6 6 6 6"/>',
    chevE:    '<path d="M9 6l6 6-6 6"/>',
    offline:  '<path d="M3 3l18 18"/><path d="M5.5 12.5a9 9 0 0 1 3.2-2.1M2 8.8A14 14 0 0 1 6 6.3M18.5 6.3A14 14 0 0 1 22 8.8M15.4 10.5a9 9 0 0 1 3.1 2"/><circle cx="12" cy="18" r="1"/>',
    filterOff:'<path d="M3 5h18l-7 8v6l-4 2v-8z"/><path d="M3 3l18 18"/>',
    empty:    '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 10h18M8 15h8"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 14) + '" height="' + (s || 14) +
           '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
           'stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function initials(n) {
    return String(n || '').split(/\s+/).slice(0, 2).map(function (w) { return w[0] || ''; }).join('');
  }

  /* ── الأنماط — مصدر واحد فلا تفترق الصفحتان بصرياً ── */
  var CSS = `
.bnf-bar{position:sticky;inset-block-start:60px;z-index:200;background:var(--bn-bg);
  border-block:1px solid var(--bn-line-soft);padding-block:var(--bn-s3);
  margin-block-end:var(--bn-s8)}
.bnf-crow-wrap{display:flex;align-items:center;gap:var(--bn-s3);margin-block-end:var(--bn-s2)}
.bnf-lbl{flex:none;font:var(--bn-t-cap);color:var(--bn-ink-3);letter-spacing:.04em}
.bnf-crow{display:flex;gap:var(--bn-s2);overflow-x:auto;flex:1;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
.bnf-crow::-webkit-scrollbar{display:none}
@media(max-width:560px){.bnf-crow-wrap{flex-direction:column;align-items:stretch;gap:6px}}

.bnf-sbar{position:relative}
.bnf-sbar::before,.bnf-sbar::after{content:"";position:absolute;inset-block:0;width:44px;
  pointer-events:none;z-index:2;opacity:0;transition:opacity var(--bn-fast)}
.bnf-sbar::before{inset-inline-start:0;background:linear-gradient(to left,transparent,var(--bn-bg))}
.bnf-sbar::after{inset-inline-end:0;background:linear-gradient(to right,transparent,var(--bn-bg))}
.bnf-sbar.has-start::before{opacity:1}
.bnf-sbar.has-end::after{opacity:1}
.bnf-arrow{position:absolute;inset-block-start:50%;transform:translateY(-50%);
  width:44px;height:44px;z-index:3;display:none;align-items:center;justify-content:center;
  border:1px solid var(--bn-line);border-radius:50%;background:var(--bn-surface);
  color:var(--bn-ink-2);cursor:pointer;box-shadow:var(--bn-sh-1);
  transition:color var(--bn-fast),border-color var(--bn-fast)}
.bnf-arrow:hover{color:var(--bn-ac);border-color:var(--bn-ac-line)}
.bnf-arrow-s{inset-inline-start:-6px}
.bnf-arrow-e{inset-inline-end:-6px}
.bnf-sbar.has-start .bnf-arrow-s{display:flex}
.bnf-sbar.has-end .bnf-arrow-e{display:flex}
.bnf-srow{display:flex;gap:var(--bn-s2);overflow-x:auto;scroll-behavior:smooth;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
.bnf-srow::-webkit-scrollbar{display:none}

.bnf-pill{flex:none;display:inline-flex;align-items:center;gap:7px;min-height:44px;
  padding-inline:var(--bn-s4);border-radius:var(--bn-r-pill);border:1px solid var(--bn-line);
  background:transparent;cursor:pointer;color:var(--bn-ink-2);
  font:400 13px/1 var(--bn-font);white-space:nowrap;
  transition:border-color var(--bn-fast),color var(--bn-fast),background var(--bn-fast)}
.bnf-pill:hover:not([disabled]){border-color:var(--bn-ac-line);color:var(--bn-ac)}
.bnf-pill.is-on{background:var(--bn-ac);color:var(--bn-ac-on);border-color:transparent}
.bnf-pill[disabled]{opacity:.42;cursor:not-allowed}
.bnf-n{font:500 11px/1 var(--bn-mono);font-variant-numeric:tabular-nums;opacity:.72}
.bnf-pill.is-on .bnf-n{opacity:.9}
.bnf-skel{flex:none;width:104px;height:44px;border-radius:var(--bn-r-pill);
  background:var(--bn-glass-tint);border:1px solid var(--bn-line-soft)}

/* الصفوف الغنية */
.bnf-rows{display:flex;flex-direction:column;gap:var(--bn-s2)}
.bnf-row{display:flex;align-items:center;gap:var(--bn-s4);padding:var(--bn-s3) var(--bn-s4);
  border-radius:var(--bn-r-lg);transition:border-color var(--bn-mid),box-shadow var(--bn-mid)}
.bnf-row:hover{border-color:var(--bn-ac-line);box-shadow:var(--bn-sh-1)}
.bnf-av{width:52px;height:52px;border-radius:var(--bn-r);flex:none;display:grid;
  place-items:center;overflow:hidden;background:var(--bn-ac-bg);color:var(--bn-ac);
  border:1px solid var(--bn-ac-line);font:500 17px/1 var(--bn-font)}
.bnf-av img{width:100%;height:100%;object-fit:cover}
.bnf-b{flex:1;min-width:0}
.bnf-name{font:500 15px/1.4 var(--bn-font);display:flex;align-items:center;gap:7px;
  margin-block-end:4px}
.bnf-name>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bnf-meta{font:var(--bn-t-cap);color:var(--bn-ink-3);display:flex;align-items:center;
  gap:var(--bn-s3);flex-wrap:wrap}
.bnf-meta i{display:inline-flex;align-items:center;gap:4px;font-style:normal}
.bnf-rate{display:inline-flex;align-items:center;gap:4px;color:var(--bn-ac);
  font:500 13px/1 var(--bn-mono);font-variant-numeric:tabular-nums;flex:none}
.bnf-act{display:flex;align-items:center;gap:var(--bn-s2);flex:none}
.bnf-wa{width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;
  border-radius:var(--bn-r-sm);flex:none;border:1px solid var(--bn-line);
  color:var(--bn-ink-2);text-decoration:none;
  transition:color var(--bn-fast),border-color var(--bn-fast)}
.bnf-wa:hover{color:var(--bn-ac);border-color:var(--bn-ac-line)}
@media(max-width:640px){
  .bnf-row{flex-wrap:wrap}
  .bnf-act{width:100%;justify-content:flex-end}
  .bnf-act .bn-btn{flex:1}
}

/* الحالات */
.bnf-state{text-align:center;padding:var(--bn-s14) var(--bn-s5)}
.bnf-state svg{width:38px;height:38px;stroke:var(--bn-ink-3);fill:none;stroke-width:1.3;
  margin-block-end:var(--bn-s3)}
.bnf-state-t{font:500 15px/1.5 var(--bn-font);color:var(--bn-ink-2)}
.bnf-state-d{font:var(--bn-t-sm);color:var(--bn-ink-3);margin-block-start:6px;
  max-width:42ch;margin-inline:auto}
.bnf-state .bn-btn{margin-block-start:var(--bn-s4)}
.bnf-skelrow{height:76px;border-radius:var(--bn-r-lg);background:var(--bn-glass-tint);
  border:1px solid var(--bn-line-soft);position:relative;overflow:hidden}
.bnf-skelrow::after{content:"";position:absolute;inset:0;transform:translateX(-100%);
  background:linear-gradient(90deg,transparent,var(--bn-glass),transparent);
  animation:bnf-sweep 1.4s infinite}
@keyframes bnf-sweep{to{transform:translateX(300%)}}
`;

  function injectCSS() {
    if (document.getElementById('bnf-style')) return;
    var s = document.createElement('style');
    s.id = 'bnf-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  /* تطبيع الشركة — مصدر واحد لأسماء الحقول */
  function normalize(c) {
    return {
      id: String(c.id), name: c.name || '—', spec: c.spec || 'مقاولات عامة',
      city: c.city || '', rating: Number(c.rating) || 0,
      verified: Boolean(c.verified), status: c.status || 'pending',
      image_url: c.image_url || '', phone: c.phone || '',
      review_count: Number(c.review_count) || 0,
      review_avg: c.review_avg != null ? Number(c.review_avg) : null,
      plan: c.subscription_plan || 'starter'
    };
  }
  function score(c) { return c.review_count > 0 ? (c.review_avg || 0) : c.rating; }

  /* صفّ شركة غني — نفس النمط في كل صفحة */
  function rowHTML(c) {
    var av = c.image_url
      ? '<div class="bnf-av"><img src="' + esc(c.image_url) + '" alt="" loading="lazy"></div>'
      : '<div class="bnf-av">' + esc(initials(c.name)) + '</div>';
    var wa = c.phone
      ? '<a class="bnf-wa" href="https://wa.me/' + esc(String(c.phone).replace(/[^\d]/g, '')) +
        '" target="_blank" rel="noopener" aria-label="واتساب ' + esc(c.name) + '">' + svg(IC.wa, 19) + '</a>'
      : '';
    return '<div class="bnf-row bn-solid">' + av +
      '<div class="bnf-b">' +
        '<div class="bnf-name"><span>' + esc(c.name) + '</span>' +
          (c.verified ? '<span class="bn-badge bn-badge-verified">' + svg(IC.check, 10) + 'موثّقة</span>' : '') +
        '</div>' +
        '<div class="bnf-meta">' +
          (c.city ? '<i>' + svg(IC.pin, 12) + esc(c.city) + '</i>' : '') +
          '<i>' + esc(c.spec) + '</i>' +
          '<span class="bnf-rate">' + svg(IC.star, 12) + score(c).toFixed(1) +
            (c.review_count ? ' (' + c.review_count + ')' : '') + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="bnf-act">' +
        '<a class="bn-btn bn-btn-sm" href="company_profile.html?id=' + esc(c.id) + '">عرض الملف</a>' + wa +
      '</div></div>';
  }

  /* ══════════════════════════════════════════════════════════ */
  function create(opts) {
    opts = opts || {};
    var API      = opts.api || '';
    var PER_PAGE = opts.perPage || 24;
    var mountSel = opts.mount || '#bnfMount';

    var S = { city: '', spec: 'all', q: '' };
    var facets = [], items = [], total = 0, pages = 0, page = 1;
    var error = false;
    var els = {};

    /* ── عنوان URL — للرجوع وللمشاركة ── */
    function toURL(push) {
      var p = new URLSearchParams();
      if (S.city) p.set('city', S.city);
      if (S.spec !== 'all') p.set('spec', S.spec);
      if (S.q) p.set('q', S.q);
      var url = location.pathname + (p.toString() ? '?' + p : '');
      try { push ? history.pushState(null, '', url) : history.replaceState(null, '', url); } catch (e) {}
    }
    function fromURL() {
      var p = new URLSearchParams(location.search);
      S.city = p.get('city') || '';
      S.spec = p.get('spec') || 'all';
      S.q    = p.get('q')    || '';
    }

    /* ── الجلب ── */
    function query(pg) {
      var p = new URLSearchParams({ page: String(pg), per_page: String(PER_PAGE) });
      if (S.city)         p.set('city', S.city);
      if (S.spec !== 'all') p.set('spec', S.spec);
      if (S.q)            p.set('q', S.q);
      return API + '/companies?' + p;
    }

    async function loadFacets() {
      try {
        var r = await fetch(API + '/companies?page=1&per_page=100', { signal: AbortSignal.timeout(12000) });
        if (r.ok) facets = ((await r.json()).items || []).map(normalize);
      } catch (e) { facets = []; }
    }

    async function load(append) {
      var pg = append ? page + 1 : 1;
      try {
        var r = await fetch(query(pg), { signal: AbortSignal.timeout(12000) });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var d = await r.json();
        var batch = (d.items || []).map(normalize);
        items = append ? items.concat(batch) : batch;
        total = d.total || 0;      /* من الخادم بنفس شرط الفلتر */
        pages = d.pages || 0;
        page  = pg;
        error = false;
      } catch (e) {
        if (!append) { items = []; total = 0; pages = 0; page = 1; }
        error = true;
      }
      build();
      emit(append);
    }

    function emit(append) {
      if (typeof opts.onResults === 'function') {
        opts.onResults({ items: items, total: total, page: page, pages: pages,
                         error: error, append: !!append, state: Object.assign({}, S),
                         hasMore: page < pages, hasFilters: hasFilters() });
      }
    }

    function hasFilters() { return !!(S.city || S.spec !== 'all' || S.q); }

    /* ── بناء واجهة الفلاتر — بعد وصول البيانات لا قبلها ── */
    function build() {
      var cityRow = els.cityRow, specRow = els.specRow;
      cityRow.innerHTML = ''; specRow.innerHTML = '';
      if (error) { els.sbar.classList.remove('has-start', 'has-end'); return; }

      var live = facets.filter(function (c) { return c.status !== 'rejected'; });
      var inSpec = function (c) { return S.spec === 'all' || c.spec === S.spec; };
      var inCity = function (c) { return !S.city || c.city === S.city; };

      /* عدّ متقاطع: عدّاد المدينة يحترم التخصص المختار والعكس،
         فلا يَعِد الرقمُ بنتيجة لا تأتي. */
      var cityCounts = {}, specCounts = {};
      live.filter(inSpec).forEach(function (c) {
        if (c.city) cityCounts[c.city] = (cityCounts[c.city] || 0) + 1;
      });
      live.filter(inCity).forEach(function (c) {
        specCounts[c.spec] = (specCounts[c.spec] || 0) + 1;
      });

      /* الفلتر النشط يبقى ظاهراً ولو صار عدّاده صفراً مع الفلتر
         الآخر، وإلا اختفى ولم يجد المستخدم ما يلغيه. */
      if (S.city && !(S.city in cityCounts)) cityCounts[S.city] = 0;
      if (S.spec !== 'all' && !(S.spec in specCounts)) specCounts[S.spec] = 0;

      function pill(label, n, active, on, disabled) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'bnf-pill' + (active ? ' is-on' : '');
        b.innerHTML = esc(label) + ' <span class="bnf-n">' + n + '</span>';
        if (disabled) b.disabled = true; else b.onclick = on;
        return b;
      }

      cityRow.appendChild(pill('كل المدن', live.filter(inSpec).length, !S.city,
        function () { setCity(''); }));
      Object.keys(cityCounts).sort().forEach(function (city) {
        var active = S.city === city;
        cityRow.appendChild(pill(city, cityCounts[city], active,
          function () { setCity(city); }, cityCounts[city] === 0 && !active));
      });

      specRow.appendChild(pill('الكل', live.filter(inCity).length, S.spec === 'all',
        function () { setSpec('all'); }));
      Object.keys(specCounts).sort(function (a, b) { return specCounts[b] - specCounts[a]; })
        .forEach(function (s) {
          var active = S.spec === s;
          specRow.appendChild(pill(s, specCounts[s], active,
            function () { setSpec(s); }, specCounts[s] === 0 && !active));
        });

      /* أظهر النشط — على الجوّال يخرج الصفّ عن الشاشة */
      [cityRow, specRow].forEach(function (row) {
        var on = row.querySelector('.bnf-pill.is-on');
        if (on && on !== row.firstElementChild) on.scrollIntoView({ block: 'nearest', inline: 'center' });
      });

      syncArrows();
    }

    function syncArrows() {
      var row = els.specRow, bar = els.sbar;
      var max = row.scrollWidth - row.clientWidth;
      if (max <= 4) { bar.classList.remove('has-start', 'has-end'); return; }
      var pos = Math.abs(row.scrollLeft);
      bar.classList.toggle('has-end', pos < max - 4);
      bar.classList.toggle('has-start', pos > 4);
    }

    /* ── التغييرات — كلها تعود إلى الصفحة ١ ── */
    function setCity(v) { S.city = v; toURL(true); load(false); }
    function setSpec(v) { S.spec = v; toURL(true); load(false); }
    function setSearch(v) { S.q = (v || '').trim(); toURL(true); load(false); }
    function clear() { S = { city: '', spec: 'all', q: '' }; toURL(true); load(false); }
    function loadMore() { return load(true); }

    /* ── الحالات — الفراغ مميَّز عن الخطأ ── */
    function stateHTML() {
      if (error) {
        return '<div class="bnf-state">' + svg(IC.offline, 38) +
          '<div class="bnf-state-t">تعذّر الاتصال بالخادم</div>' +
          '<div class="bnf-state-d">لم نتمكّن من تحميل قائمة الشركات. تحقّق من اتصالك ثم أعد المحاولة.</div>' +
          '<button class="bn-btn" type="button" data-bnf-retry>إعادة المحاولة</button></div>';
      }
      if (hasFilters()) {
        var bits = [];
        if (S.city) bits.push(S.city);
        if (S.spec !== 'all') bits.push(S.spec);
        if (S.q) bits.push('«' + S.q + '»');
        return '<div class="bnf-state">' + svg(IC.filterOff, 38) +
          '<div class="bnf-state-t">لا توجد شركات بهذا الفلتر</div>' +
          '<div class="bnf-state-d">لا نتائج لـ ' + esc(bits.join(' + ')) + '.</div>' +
          '<button class="bn-btn" type="button" data-bnf-clear>إزالة الفلاتر</button></div>';
      }
      return '<div class="bnf-state">' + svg(IC.empty, 38) +
        '<div class="bnf-state-t">لا توجد شركات بعد</div></div>';
    }

    /** يرسم النتيجة في حاوية: صفوفاً أو حالة فراغ/خطأ. */
    function renderInto(el) {
      var vis = items.filter(function (c) { return c.status !== 'rejected'; });
      if (error || !vis.length) {
        el.innerHTML = stateHTML();
        var rt = el.querySelector('[data-bnf-retry]');
        if (rt) rt.onclick = async function () {
          rt.disabled = true; rt.textContent = 'جارٍ المحاولة...';
          await loadFacets(); await load(false);
          renderInto(el);
        };
        var cl = el.querySelector('[data-bnf-clear]');
        if (cl) cl.onclick = function () { clear(); };
        return;
      }
      el.className = 'bnf-rows';
      el.innerHTML = vis.map(rowHTML).join('');
    }

    /* ── التركيب ── */
    function mount() {
      injectCSS();
      var host = document.querySelector(mountSel);
      host.innerHTML =
        '<div class="bnf-crow-wrap">' +
          '<span class="bnf-lbl">المدينة</span>' +
          '<div class="bnf-crow" data-bnf-city>' +
            '<div class="bnf-skel"></div><div class="bnf-skel"></div><div class="bnf-skel"></div>' +
          '</div>' +
        '</div>' +
        '<div class="bnf-sbar" data-bnf-sbar>' +
          '<button class="bnf-arrow bnf-arrow-s" type="button" data-bnf-prev aria-label="تخصصات سابقة">' + svg(IC.chevS, 18) + '</button>' +
          '<button class="bnf-arrow bnf-arrow-e" type="button" data-bnf-next aria-label="تخصصات تالية">' + svg(IC.chevE, 18) + '</button>' +
          '<div class="bnf-srow" data-bnf-spec>' +
            '<div class="bnf-skel"></div><div class="bnf-skel"></div>' +
            '<div class="bnf-skel"></div><div class="bnf-skel"></div>' +
          '</div>' +
        '</div>';

      els.cityRow = host.querySelector('[data-bnf-city]');
      els.specRow = host.querySelector('[data-bnf-spec]');
      els.sbar    = host.querySelector('[data-bnf-sbar]');

      els.specRow.addEventListener('scroll', syncArrows, { passive: true });
      window.addEventListener('resize', syncArrows);
      host.querySelector('[data-bnf-prev]').onclick = function () {
        els.specRow.scrollBy({ left: 240, behavior: 'smooth' });
      };
      host.querySelector('[data-bnf-next]').onclick = function () {
        els.specRow.scrollBy({ left: -240, behavior: 'smooth' });
      };
      window.addEventListener('popstate', function () { fromURL(); load(false); });
    }

    async function init() {
      mount();
      fromURL();
      await loadFacets();
      await load(false);
      toURL(false);
    }

    return {
      init: init, state: S, setCity: setCity, setSpec: setSpec,
      setSearch: setSearch, clear: clear, loadMore: loadMore,
      renderInto: renderInto, hasFilters: hasFilters,
      get items() { return items; },
      get total() { return total; },
      get pages() { return pages; },
      get page()  { return page; },
      get error() { return error; },
      get facets() { return facets; }
    };
  }

  window.BunyanFilters = {
    create: create, normalize: normalize, score: score,
    rowHTML: rowHTML, icons: IC, svg: svg, esc: esc, initials: initials
  };
})();
