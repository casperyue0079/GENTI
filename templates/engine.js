(function () {
  "use strict";

  const container = document.getElementById("app");
  let currentIndex = 0;
  const answers = {};

  function getData() {
    return window.__TEST_DATA__;
  }

  function isAxisMode() {
    return getData().mode !== "多维度";
  }

  // ===== MULTI-AXIS SCORING =====

  function computeAxisScores(data, answers) {
    const raw = {};
    const maxPossible = {};
    data.axes.forEach(function (a) {
      raw[a.id] = 0;
      maxPossible[a.id] = 0;
    });
    data.questions.forEach(function (q) {
      const ans = answers[q.id];
      if (ans === undefined) return;
      raw[q.primary_axis_id] += ans;
      maxPossible[q.primary_axis_id] += 2;
      (q.weak_axes || []).forEach(function (w) {
        if (raw[w.axis_id] !== undefined) {
          raw[w.axis_id] += ans * w.coefficient;
          maxPossible[w.axis_id] += 2 * w.coefficient;
        }
      });
    });
    const normalized = {};
    for (var id in raw) {
      var cap = maxPossible[id];
      normalized[id] = cap > 0 ? Math.max(-1, Math.min(1, raw[id] / cap)) : 0;
    }
    return normalized;
  }

  // ===== MULTI-DIMENSION SCORING =====

  function computeDimScores(data, answers) {
    var raw = {};
    var maxAbs = {};
    data.dimensions.forEach(function (d) {
      raw[d.id] = 0;
      maxAbs[d.id] = 0;
    });
    data.questions.forEach(function (q) {
      var optIdx = answers[q.id];
      if (optIdx === undefined || optIdx < 0 || optIdx >= q.options.length) return;
      var effects = q.options[optIdx].effects;
      for (var dimId in effects) {
        if (raw[dimId] !== undefined) {
          raw[dimId] += effects[dimId];
          maxAbs[dimId] += Math.abs(effects[dimId]);
        }
      }
    });
    var normalized = {};
    for (var dimId in raw) {
      var cap = maxAbs[dimId];
      normalized[dimId] = cap > 0 ? Math.max(-1, Math.min(1, raw[dimId] / cap)) : 0;
    }
    return normalized;
  }

  // ===== SHARED MATH =====

  function cosineSimilarity(vecA, vecB) {
    var dot = 0, magA = 0, magB = 0;
    var allKeys = {};
    for (var k in vecA) allKeys[k] = true;
    for (var k2 in vecB) allKeys[k2] = true;
    for (var key in allKeys) {
      var a = vecA[key] || 0;
      var b = vecB[key] || 0;
      dot += a * b;
      magA += a * a;
      magB += b * b;
    }
    if (magA === 0 || magB === 0) return 0;
    return dot / (Math.sqrt(magA) * Math.sqrt(magB));
  }

  function mapNormalResult(scores, normalResults) {
    var best = null, bestSim = -999;
    normalResults.forEach(function (r) {
      var sim = cosineSimilarity(scores, r.dimension_combo);
      if (sim > bestSim) { bestSim = sim; best = r; }
    });
    return best;
  }

  function matchArchetype(scores, archetypes) {
    var best = null, bestSim = -999;
    archetypes.forEach(function (a) {
      var sim = cosineSimilarity(scores, a.vector);
      if (sim > bestSim) { bestSim = sim; best = a; }
    });
    return { archetype: best, similarity: bestSim };
  }

  // ===== AXIS RARE RESULTS =====

  function checkAxisRareResults(scores, questions, answers, rareResults) {
    var triggered = [];
    (rareResults || []).forEach(function (rr) {
      var dimsMet = (rr.threshold_conditions || []).every(function (c) {
        return (scores[c.axis_id] || 0) * c.direction >= c.threshold;
      });
      if (!dimsMet) return;
      var hits = 0;
      questions.forEach(function (q) {
        if (q.is_special && q.linked_rare_id === rr.id) {
          if (Math.abs(answers[q.id] || 0) >= 1) hits++;
        }
      });
      if (hits >= (rr.min_special_hits || 1)) triggered.push(rr);
    });
    return triggered;
  }

  // ===== DIMENSION RARE TAGS =====

  function checkDimRareTags(scores, questions, answers, rareTags) {
    var clusterHits = {};
    questions.forEach(function (q) {
      if (q.is_special && q.special_cluster) {
        var optIdx = answers[q.id];
        if (optIdx !== undefined && optIdx >= 0 && optIdx < q.options.length) {
          var effects = q.options[optIdx].effects;
          for (var k in effects) {
            if (Math.abs(effects[k]) >= 1) {
              clusterHits[q.special_cluster] = (clusterHits[q.special_cluster] || 0) + 1;
              break;
            }
          }
        }
      }
    });
    var triggered = [];
    (rareTags || []).forEach(function (rt) {
      if (evalRules(rt.rules, scores, clusterHits)) triggered.push(rt);
    });
    return triggered;
  }

  function evalRules(rules, scores, clusterHits) {
    for (var gate in rules) {
      var ruleList = rules[gate];
      var results = ruleList.map(function (r) { return evalSingleRule(r, scores, clusterHits); });
      if (gate === "all" && results.indexOf(false) !== -1) return false;
      if (gate === "any" && results.indexOf(true) === -1) return false;
    }
    return true;
  }

  function evalSingleRule(rule, scores, clusterHits) {
    if (rule.type === "dimension_min") return (scores[rule.dimension] || 0) >= rule.value;
    if (rule.type === "dimension_max") return (scores[rule.dimension] || 0) <= rule.value;
    if (rule.type === "special_cluster_min_hits") return (clusterHits[rule.cluster] || 0) >= rule.value;
    return false;
  }

  // ===== RENDERING =====

  function renderStart() {
    var data = getData();
    var qLen = data.questions.length;
    container.innerHTML =
      '<div class="start-page">' +
        '<h1>' + (data.title || "人格测试") + '</h1>' +
        '<p>' + (data.description || "发现你的隐藏人格类型") + '</p>' +
        '<p class="question-count">共 ' + qLen + ' 道题</p>' +
        '<button class="btn btn-primary" onclick="window.__startTest()">开始测试</button>' +
      '</div>';
  }

  window.__startTest = function () {
    currentIndex = 0;
    for (var k in answers) delete answers[k];
    renderQuestion();
  };

  function renderQuestion() {
    var data = getData();
    var q = data.questions[currentIndex];
    var total = data.questions.length;
    var pct = (currentIndex / total * 100).toFixed(0);

    if (isAxisMode()) {
      renderAxisQuestion(q, total, pct);
    } else {
      renderDimQuestion(q, total, pct);
    }
  }

  // axis-mode question (5 options, value-based)
  function renderAxisQuestion(q, total, pct) {
    var selected = answers[q.id];
    var optionsHtml = q.options.map(function (opt, i) {
      return '<button class="option-btn ' + (selected === opt.value ? "selected" : "") + '"' +
        ' onclick="window.__selectAxisOption(\'' + q.id + '\',' + opt.value + ')">' + opt.text + '</button>';
    }).join("");

    container.innerHTML =
      '<div class="progress-text">' + (currentIndex + 1) + ' / ' + total + '</div>' +
      '<div class="progress-bar"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
      '<div class="question-card"><div class="question-text">' + q.text + '</div><div class="options">' + optionsHtml + '</div></div>' +
      '<div class="nav-buttons">' +
        (currentIndex > 0 ? '<button class="btn btn-secondary" onclick="window.__prevQ()">上一题</button>' : '<div></div>') +
        '<button class="btn btn-primary" ' + (selected === undefined ? "disabled" : "") + ' onclick="window.__nextQ()">' +
        (currentIndex === total - 1 ? "查看结果" : "下一题") + '</button></div>';
  }

  // dim-mode question (3 options, index-based)
  function renderDimQuestion(q, total, pct) {
    var selected = answers[q.id];
    var optionsHtml = q.options.map(function (opt, i) {
      return '<button class="option-btn ' + (selected === i ? "selected" : "") + '"' +
        ' onclick="window.__selectDimOption(\'' + q.id + '\',' + i + ')">' + opt.text + '</button>';
    }).join("");

    container.innerHTML =
      '<div class="progress-text">' + (currentIndex + 1) + ' / ' + total + '</div>' +
      '<div class="progress-bar"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
      '<div class="question-card"><div class="question-text">' + (q.stem || q.text) + '</div><div class="options">' + optionsHtml + '</div></div>' +
      '<div class="nav-buttons">' +
        (currentIndex > 0 ? '<button class="btn btn-secondary" onclick="window.__prevQ()">上一题</button>' : '<div></div>') +
        '<button class="btn btn-primary" ' + (selected === undefined ? "disabled" : "") + ' onclick="window.__nextQ()">' +
        (currentIndex === total - 1 ? "查看结果" : "下一题") + '</button></div>';
  }

  window.__selectAxisOption = function (qId, value) { answers[qId] = value; renderQuestion(); };
  window.__selectDimOption = function (qId, idx) { answers[qId] = idx; renderQuestion(); };
  window.__selectOption = function (qId, value) { answers[qId] = value; renderQuestion(); };

  window.__prevQ = function () { if (currentIndex > 0) { currentIndex--; renderQuestion(); } };
  window.__nextQ = function () {
    var data = getData();
    if (currentIndex < data.questions.length - 1) { currentIndex++; renderQuestion(); }
    else { renderResult(); }
  };

  // ===== RESULT =====

  function renderResult() {
    if (isAxisMode()) { renderAxisResult(); }
    else { renderDimResult(); }
  }

  function renderAxisResult() {
    var data = getData();
    var scores = computeAxisScores(data, answers);
    var normal = mapNormalResult(scores, data.normal_results);
    var rares = checkAxisRareResults(scores, data.questions, answers, data.rare_results || []);

    var overrideName = null, overrideDesc = null;
    var rareTags = [];
    var mainImg = normal && normal.image_path ? normal.image_path : null;
    rares.forEach(function (rr) {
      if (rr.type === "覆盖") {
        overrideName = rr.name;
        overrideDesc = rr.description;
        if (rr.image_path) mainImg = rr.image_path;
      } else {
        rareTags.push({ name: rr.name, image_path: rr.image_path || null });
      }
    });

    var resolved = resolveDisplayName(data.naming_mode, overrideName || (normal ? normal.name : "未知"), normal);
    var mainDesc = overrideDesc || (normal ? normal.description : "");

    container.innerHTML = buildResultHTML(resolved.display, resolved.subtitle, mainDesc, mainImg, null, rareTags, data.axes.map(function (a) {
      return { low: a.left_name, high: a.right_name, score: scores[a.id] || 0 };
    }));
  }

  function renderDimResult() {
    var data = getData();
    var scores = computeDimScores(data, answers);
    var match = matchArchetype(scores, data.archetypes);
    var arch = match.archetype;
    var similarity = match.similarity;
    var rares = checkDimRareTags(scores, data.questions, answers, data.rare_tags || []);
    var simPct = (similarity * 100).toFixed(0);

    var resolved = resolveDisplayName(data.naming_mode, arch ? arch.name : "未知", arch);
    var mainDesc = arch ? arch.description : "";
    var imgPath = arch && arch.image_path ? arch.image_path : null;

    container.innerHTML = buildResultHTML(resolved.display, resolved.subtitle, mainDesc, imgPath, simPct, rares.map(function (t) {
      return { name: t.name, image_path: t.image_path || null };
    }), data.dimensions.map(function (d) {
      return { low: d.low_label, high: d.high_label, score: scores[d.id] || 0 };
    }));
  }

  function resolveDisplayName(namingMode, abstractName, resultObj) {
    var refName = resultObj && resultObj.reference_name ? resultObj.reference_name : null;
    var refSrc = resultObj && resultObj.reference_source ? resultObj.reference_source : null;

    if (namingMode === "角色对标" && refName) {
      return { display: refName, subtitle: refSrc ? "（" + refSrc + "）" : "" };
    }
    if (namingMode === "两者兼用" && refName) {
      var sub = "类似于 " + refName;
      if (refSrc) sub += "（" + refSrc + "）";
      return { display: abstractName, subtitle: sub };
    }
    return { display: abstractName, subtitle: "" };
  }

  // Shared result layout builder (SBTI-style)
  function buildResultHTML(name, subtitle, desc, imgPath, matchPct, rareTagItems, dims) {
    var posterHtml = imgPath
      ? '<div class="poster-box"><img src="' + imgPath + '" alt="' + name + '"></div>'
      : '';

    var matchHtml = matchPct ? '<div class="match-badge">匹配度 ' + matchPct + '%</div>' : '';

    var rareHtml = rareTagItems && rareTagItems.length
      ? '<div class="rare-tags">' + rareTagItems.map(function (t) {
          var img = t.image_path
            ? '<img src="' + t.image_path + '" alt="" class="rare-tag-img">'
            : '';
          return '<span class="rare-tag">' + img + '<span class="rare-tag-text">\u2728 ' + t.name + '</span></span>';
        }).join("") + '</div>'
      : '';

    var dimHtml = dims.map(function (d) {
      var pct = ((d.score + 1) / 2 * 100).toFixed(1);
      return '<div class="dim-row">' +
        '<div class="dim-labels"><span>' + d.low + '</span><span>' + d.high + '</span></div>' +
        '<div class="dim-track"><div class="dim-indicator" style="left:' + pct + '%"></div></div>' +
        '</div>';
    }).join("");

    var subtitleHtml = subtitle ? '<div class="type-subtitle">' + subtitle + '</div>' : '';

    return '<div class="result-page">' +
      '<div class="header"><p>你的测试结果</p></div>' +
      '<div class="result-top">' +
        posterHtml +
        '<div class="type-box">' +
          '<div class="type-kicker">YOUR TYPE</div>' +
          '<div class="type-name">' + name + '</div>' +
          subtitleHtml +
          matchHtml +
        '</div>' +
      '</div>' +
      rareHtml +
      '<div class="result-desc-box">' + desc + '</div>' +
      '<div class="dimension-bars">' + dimHtml + '</div>' +
      '<div class="result-actions">' +
        '<button class="btn btn-secondary restart-btn" onclick="window.__restart()">重新测试</button>' +
      '</div>' +
    '</div>';
  }

  window.__restart = function () {
    currentIndex = 0;
    for (var k in answers) delete answers[k];
    renderStart();
  };

  renderStart();
})();
