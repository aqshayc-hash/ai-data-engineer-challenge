# 🚀 Quick Start: Complete Patient Journey Analytics Pipeline

## What You Have

✅ **Complete end-to-end system** for analyzing patient journeys from Reddit data

- **Phase 1**: Environment setup (pyproject.toml, Docker, config)
- **Phase 2**: Reddit data ingestion (5 Dagster assets)
- **Phase 3**: LLM-powered extraction (7 Dagster assets)
- **Phase 4**: Patient journey analytics (12 Dagster assets)

**Total: 24 Dagster assets, 4 specialized jobs, 55+ unit tests**

---

## 📋 Pre-requisites

1. **Docker installed** - For Dagster + PostgreSQL
2. **Redis credentials** (in `.env`):
   - Reddit: Get from https://www.reddit.com/prefs/apps
   - Gemini: Get from https://aistudio.google.com/apikey

3. **Environment file** - Copy `.env.example` to `.env` and add credentials

---

## 🏃 Quick Start (10 minutes)

### Step 1: Prepare Environment

```bash
# Copy environment template
copy .env.example .env

# Edit .env and add:
# - REDDIT_CLIENT_ID=your_id
# - REDDIT_CLIENT_SECRET=your_secret
# - REDDIT_USER_AGENT=your_agent
# - GEMINI_API_KEY=your_key
```

### Step 2: Start Dagster & Database

```bash
# Start complete Docker stack
docker compose up

# This starts:
# - PostgreSQL (metadata storage)
# - Dagster WebServer (http://localhost:3000)  
# - Dagster Daemon (job orchestration)
```

### Step 3: Open Dagster UI

Visit: **http://localhost:3000**

### Step 4: Run Complete Pipeline

1. Click **"end_to_end_job"** in left sidebar
2. Click **"Materialize"** button
3. Watch execution progress:
   - ✅ Reddit ingestion (5 assets)
   - ✅ LLM extraction (7 assets)
   - ✅ Analytics computation (12 assets)

**Total time**: ~35-40 minutes (depends on data size & API rate limits)

### Step 5: View Results

Click any asset to see output:
- **patient_journey_analytics_summary** - Overall findings
- **symptom_to_diagnosis_timeline** - Patient journey timelines
- **medication_side_effect_associations** - Drug safety insights
- **unmet_needs_summary** - Patient information gaps
- And 8 more analytics...

---

## 📊 What Each Phase Produces

### Phase 1: Environment
- ✅ Configuration files
- ✅ Docker stack
- ✅ Dependency management

### Phase 2: Reddit Ingestion
```
reddit_ingestion_job outputs:
├── raw_posts_json (numbered posts with comments)
├── posts_metadata (summary statistics)
└── Ready for LLM extraction
```

### Phase 3: LLM Extraction  
```
llm_extraction_job outputs:
├── extracted_post_events (structured event data)
├── extracted_comment_events (event data from comments)
├── all_extracted_events (combined, deduplicated)
├── symptom_mentions (focused extraction)
├── medication_mentions (focused extraction)
└── extraction_quality_metrics (confidence analysis)
```

### Phase 4: Patient Journey Analytics
```
analytics_job outputs:
├── Temporal Analysis
│  ├── symptom_to_diagnosis_timeline
│  └── treatment_phase_duration
├── Co-occurrence Analysis  
│  ├── symptom_cooccurrence_mapping
│  └── medication_side_effect_associations
├── Emotional Journey
│  ├── emotional_journey_phases
│  └── emotional_state_events
├── Unmet Needs
│  ├── unmet_needs_identification
│  └── unmet_needs_summary
├── Reporting
│  ├── event_type_frequency
│  ├── treatment_mention_frequency
│  └── symptom_mention_frequency
└── Summary
   └── patient_journey_analytics_summary (aggregated findings)
```

---

## 🎯 Common Tasks

### Run Only Analytics (Skip Reddit + LLM)

If you already have `all_extracted_events`:

1. In Dagster UI, click **"analytics_job"**
2. Click **"Materialize"**
3. ~5 minutes execution time

### Run Only One Asset

1. Click specific asset in Dagster UI
2. Click **"Materialize Single"**
3. View output

### View Specific Analytics

| Analytics | Asset Name | Contains |
|-----------|-----------|----------|
| **Timelines** | symptom_to_diagnosis_timeline | Time between symptom → diagnosis |
| **Treatment** | treatment_phase_duration | How long on each treatment |
| **Symptoms** | symptom_cooccurrence_mapping | Which symptoms occur together |
| **Medications** | medication_side_effect_associations | Drugs & reported side effects |
| **Emotional** | emotional_journey_phases | Patient journey sentiment |
| **Gaps** | unmet_needs_summary | Information patients are seeking |
| **Summary** | patient_journey_analytics_summary | All findings combined |

---

## 📈 Example Findings (What Analytics Reveal)

### Temporal Findings
```json
"Most patients experience 6-12 months from symptom to diagnosis"
"Average time on treatment before switching: 3-6 months"
```

### Co-occurrence Findings
```json
"Abdominal pain + diarrhea mentioned together 45 times"
"Fatigue + joint pain are common co-occurring symptoms"
```

### Medication Findings
```json
"Adalimumab: 45 mentions, most common side effect: injection site pain"
"Mesalamine: 23 mentions, side effect profile: headaches, nausea"
```

### Patient Journey Findings
```json
"Symptom phase: neutral/negative sentiment (frustration)"
"Diagnosis phase: mixed sentiment (relief + concern)"
"Treatment phase: positive trend (improving)"
"Management phase: sustained improvement"
```

### Unmet Needs
```json
"Top gaps: timeline expectations, medication alternatives, lifestyle guidance"
"42 unmet needs identified across dataset"
```

---

## ✅ Validation Checklist

After running pipeline:

- [ ] **Reddit ingestion**: raw_posts_json has posts data
- [ ] **LLM extraction**: all_extracted_events populated (check event_type_frequency)
- [ ] **Temporal analysis**: symptom_to_diagnosis_timeline has results
- [ ] **Co-occurrence**: symptom_cooccurrence_mapping shows symptom pairs
- [ ] **Sentiment**: emotional_journey_phases has phase distribution
- [ ] **Unmet needs**: unmet_needs_summary shows identified gaps
- [ ] **Overall**: patient_journey_analytics_summary aggregates all

---

## 🔧 Troubleshooting

### "Connection refused" to Dagster UI
```bash
# Make sure Docker is running
docker compose ps

# If services not up, restart
docker compose restart
```

### "No Reddit data"
```bash
# Check credentials in .env
# Verify Reddit API access at: https://www.reddit.com/prefs/apps

# Or configure different subreddit in .env
TARGET_SUBREDDIT=Crohns  # Try another subreddit
```

### "LLM extraction empty"
```bash
# Check GEMINI_API_KEY in .env
# Verify API key at: https://aistudio.google.com/apikey
# Check rate limit (60 req/min for free tier)
```

### "Analytics assets not showing"
```bash
# Ensure LLM extraction completed first
# Check all_extracted_events has data
# Reload Dagster UI (F5)
```

---

## 📚 Documentation

For detailed information, see:

| Document | Purpose |
|----------|---------|
| [PATIENT_JOURNEY_ANALYTICS.md](PATIENT_JOURNEY_ANALYTICS.md) | Complete analytics guide |
| [LLM_EXTRACTION.md](LLM_EXTRACTION.md) | LLM extraction details |
| [REDDIT_INGESTION.md](REDDIT_INGESTION.md) | Reddit ingestion guide |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Overall project status |
| [PHASE_4_IMPLEMENTATION_SUMMARY.md](PHASE_4_IMPLEMENTATION_SUMMARY.md) | Phase 4 details |

---

## 🎓 Key Concepts

### PatientJourneyEvent
The core data model flowing through pipeline:
```python
{
    "event_id": "unique_id",
    "event_type": "symptom|diagnosis|treatment|...",
    "description": "What happened",
    "mentioned_entity": "The entity mentioned",
    "confidence": 0.95,  # 0-1 score
    "quote": "Original text from Reddit",
    "timestamp": "when_posted"
}
```

### Confidence Scores
- **0.95+**: High confidence (use directly)
- **0.80-0.94**: Medium confidence (review manually)
- **<0.80**: Low confidence (likely to discard)

All analytics use confidence-weighted calculations.

---

## 🚨 Important Notes

### Medical Data Warning
- This system extracts from Reddit (non-medical source)
- Confidence scores reflect extraction uncertainty
- **NOT for clinical decision making**
- Use only for research/insights

### Privacy
- Reddit data is public (from r/subreddit)
- No personal identifiable information collected
- Aggregated analysis only

### Limitations
- Timeline estimates based on post timestamps
- Co-occurrence ≠ causation
- Medication names not normalized (brand vs generic)

---

## 🎯 Next Steps

1. **Run pipeline** with `docker compose up` and Materialize end_to_end_job
2. **Explore outputs** in Dagster UI
3. **Review findings** from patient_journey_analytics_summary
4. **Customize analytics** by modifying prompts or analyzer thresholds
5. **Persist results** to database for visualization/reporting
6. **Build dashboards** from analytics outputs
7. **Integrate downstream** with ML models or reports

---

## 💡 Pro Tips

### Export Data
```bash
# Individual asset outputs visible in Dagster UI
# Copy JSON from asset output and save to file
# Use for Excel/Tableau/Power BI analysis
```

### Modify Analytics
```bash
# Edit analyzer confidence thresholds
# Change unmet needs keywords  
# Adjust sentiment classification

# In: src/mama_health/analytics.py
# Then re-run analytics_job
```

### Add New Subreddit
```bash
# Edit .env
TARGET_SUBREDDIT=YourSubreddit

# Re-run: reddit_ingestion_job → llm_extraction_job → analytics_job
```

---

## 📞 Support

All components have comprehensive documentation:
- Each .py file has docstrings
- Type hints throughout
- Error messages are descriptive
- Logging enabled for debugging

**Key log files:**
```bash
docker compose logs dagster-webserver  # UI logs
docker compose logs dagster-daemon      # Job execution logs
```

---

## 🎉 You're All Set!

Everything is ready to run. With 4 commands:

```bash
docker compose up              # Start Docker
# Open http://localhost:3000   # View Dagster
# Click end_to_end_job → Materialize
# Wait 35-40 minutes for complete analysis
```

**Result**: Comprehensive patient journey insights from Reddit data! 📊

---

**Questions?** Check the documentation files or examine asset outputs in Dagster UI.

**Ready to explore patient journeys!** 🚀
