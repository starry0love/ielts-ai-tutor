<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <aside class="fixed inset-y-0 left-0 w-64 border-r border-slate-200 bg-white px-5 py-6">
      <p class="text-sm text-slate-500">IELTS AI Tutor</p>
      <h1 class="mt-2 text-2xl font-semibold">AI 学习导师</h1>
      <p class="mt-2 text-sm leading-6 text-slate-500">先理解你，再安排每天怎么学。</p>
      <nav class="mt-7 space-y-1">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="w-full rounded-md px-3 py-2 text-left text-sm font-medium"
          :class="activeView === item.id ? 'bg-emerald-50 text-emerald-700' : 'text-slate-600 hover:bg-slate-100'"
          @click="activeView = item.id"
        >
          {{ item.label }}
        </button>
      </nav>
      <div class="absolute bottom-6 left-5 right-5 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
        <p class="text-slate-500">导师状态</p>
        <p class="mt-1 font-semibold">{{ profile.onboarding_completed ? styleLabel : "等待入门对话" }}</p>
      </div>
    </aside>

    <main class="ml-64 px-8 py-7">
      <p
        v-if="operationMessage"
        class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800"
      >
        {{ operationMessage }}
      </p>

      <section v-if="needsAiSetup" class="space-y-5">
        <Header title="连接你的大模型" subtitle="开源版不内置 API Key。先连接一个兼容 OpenAI 接口的大模型，再开始入门画像和每日计划。" />
        <section class="rounded-md border border-slate-200 bg-white p-5">
          <div class="grid gap-4 md:grid-cols-2">
            <label class="field-label">
              <span>接口类型</span>
              <select v-model="aiConfig.provider" class="field-control">
                <option value="openai-compatible">OpenAI 兼容接口</option>
              </select>
            </label>
            <label class="field-label">
              <span>模型名称</span>
              <input v-model="aiConfig.model" class="field-control" placeholder="例如 gpt-4o-mini 或你的模型名" />
            </label>
            <label class="field-label md:col-span-2">
              <span>接口地址</span>
              <input v-model="aiConfig.base_url" class="field-control" placeholder="例如 https://api.openai.com/v1" />
            </label>
            <label class="field-label md:col-span-2">
              <span>API Key</span>
              <input v-model="aiConfig.api_key" type="password" class="field-control" placeholder="只保存在你本机的配置文件中" />
            </label>
          </div>
          <div class="mt-4 grid gap-4 md:grid-cols-2">
            <label class="field-label">
              <span>超时时间（秒）</span>
              <input v-model.number="aiConfig.timeout_seconds" type="number" min="5" class="field-control" />
            </label>
            <label class="field-label">
              <span>最大输出长度</span>
              <input v-model.number="aiConfig.max_tokens" type="number" min="256" class="field-control" />
            </label>
          </div>
          <div class="mt-5 flex flex-wrap gap-2">
            <button class="btn-secondary" :disabled="isBusy || !canSaveAiConfig" @click="testAiConfig">
              {{ busyAction === "ai-test" ? "正在测试连接..." : "测试连接" }}
            </button>
            <button class="btn-primary" :disabled="isBusy || !canSaveAiConfig" @click="saveAiConfig">
              {{ busyAction === "ai-config" ? "正在测试并保存..." : "测试并保存" }}
            </button>
          </div>
        </section>
      </section>

      <section v-else-if="activeView === 'today'" class="space-y-5">
        <Header title="今日计划" :subtitle="todayLabel" />
        <div class="flex flex-wrap gap-2">
          <button class="btn-secondary" :disabled="isBusy" @click="openOnboarding">
            {{ profile.onboarding_completed ? "更新入门画像" : "开始入门对话" }}
          </button>
          <button v-if="profile.onboarding_completed" class="btn-primary" :disabled="isBusy" @click="startPlanDiscussion">
            {{ discussionButtonLabel }}
          </button>
        </div>

        <section v-if="!profile.onboarding_completed" class="rounded-md border border-amber-200 bg-amber-50 p-5">
          <p class="font-semibold text-amber-900">先完成入门对话</p>
          <p class="mt-2 text-sm text-amber-900">
            导师需要先知道目标、基础、每天学习时间、学习方式和偏好。保存后会自动起草今日大纲，不需要再点一次按钮。
          </p>
        </section>

        <section class="rounded-md border border-slate-200 bg-white p-5">
          <p class="text-sm text-slate-500">导师判断</p>
          <h3 class="mt-2 text-xl font-semibold">{{ todayPlanTitle }}</h3>
          <p class="mt-2 text-sm leading-6 text-slate-600">{{ todayPlanReason }}</p>
          <p v-if="statusMessage" class="mt-3 text-sm text-emerald-700">{{ statusMessage }}</p>
        </section>

        <section v-if="planDiscussion" class="rounded-md border border-emerald-200 bg-white p-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-sm font-medium text-emerald-700">今日沟通</p>
              <h3 class="mt-1 text-lg font-semibold">导师起草的大纲</h3>
            </div>
            <span class="rounded-md bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">待确认</span>
          </div>
          <div class="mt-4 grid gap-4 md:grid-cols-3">
            <Info title="历史印象" :text="planDiscussion.history_summary" />
            <Info title="学习模式" :text="planDiscussion.learner_pattern" />
            <Info title="今日建议" :text="planDiscussion.today_recommendation" />
          </div>
          <div v-if="planQuestions.length" class="mt-4 rounded-md bg-slate-50 p-4">
            <p class="text-sm font-semibold">导师想先确认</p>
            <ul class="mt-2 space-y-2 text-sm leading-6 text-slate-600">
              <li v-for="question in planQuestions" :key="question">- {{ question }}</li>
            </ul>
          </div>
          <textarea
            v-model="planFeedback"
            rows="3"
            class="mt-4 w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="告诉导师今天真实情况：可用时间、精力、想轻一点还是挑战一点。"
          />
          <div class="mt-4 flex justify-end gap-2">
            <button class="btn-secondary" :disabled="isBusy" @click="generatePlan">
              {{ busyAction === "generate-plan" ? "正在生成，请勿重复提交" : "确认生成今日计划" }}
            </button>
            <button class="btn-primary" :disabled="isBusy" @click="regeneratePlan">
              {{ busyAction === "regenerate-plan" ? "正在根据补充生成，请勿重复提交" : "根据补充生成今日计划" }}
            </button>
          </div>
        </section>

        <article v-for="task in todayPlan.tasks" :key="task.id" class="rounded-md border border-slate-200 bg-white p-5">
          <p class="text-xs font-semibold uppercase text-emerald-700">{{ task.module }}</p>
          <h3 class="mt-1 text-lg font-semibold">{{ task.title }}</h3>
          <p class="mt-2 text-sm leading-6 text-slate-600">{{ task.description }}</p>
          <p class="mt-3 text-sm text-slate-500">完成证据：{{ task.completion_criteria }}</p>
        </article>
      </section>

      <section v-if="activeView === 'writing'" class="space-y-5">
        <Header title="写作批改" subtitle="贴入自己的作文，导师评价、修改，并把写作信号纳入后续计划。" />
        <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section class="rounded-md border border-slate-200 bg-white p-5">
            <select v-model="writingForm.task_type" class="rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="task2">Task 2</option>
              <option value="task1">Task 1</option>
            </select>
            <textarea v-model="writingForm.prompt" rows="3" class="mt-4 w-full rounded-md border border-slate-300 px-3 py-2" placeholder="题目或写作要求，可选。" />
            <textarea v-model="writingForm.essay_text" rows="14" class="mt-4 w-full rounded-md border border-slate-300 px-3 py-2" placeholder="把自己的作文或段落贴到这里。" />
            <div class="mt-4 flex justify-between gap-2">
              <button class="btn-primary" :disabled="isBusy || !writingForm.essay_text.trim()" @click="submitWriting">
                {{ busyAction === "writing" ? "导师正在批改，请勿重复提交" : "提交给导师批改" }}
              </button>
            </div>
          </section>
          <aside class="rounded-md border border-slate-200 bg-white p-5">
            <p class="text-sm text-slate-500">导师反馈</p>
            <div v-if="writingFeedback" class="mt-3 space-y-3 text-sm leading-6">
              <p class="text-2xl font-semibold">Band {{ writingFeedback.estimated_band || "-" }}</p>
              <p>{{ parsedWriting.summary || "反馈已保存。" }}</p>
              <div v-for="issue in parsedWriting.top_issues || []" :key="issue.title || issue.category" class="rounded-md bg-slate-50 p-3">
                <p class="font-semibold">{{ issue.title || issue.category }}</p>
                <p>{{ issue.fix || issue.evidence || issue.comment || "建议在复盘里记录。" }}</p>
              </div>
              <p v-if="parsedWriting.band_75_rewrite" class="whitespace-pre-wrap rounded-md bg-emerald-50 p-3">{{ parsedWriting.band_75_rewrite }}</p>
            </div>
            <p v-else class="mt-3 text-sm text-slate-500">提交后会显示评价和修改建议。</p>
          </aside>
        </div>
      </section>

      <section v-if="activeView === 'review'" class="space-y-5">
        <Header title="每日复盘" subtitle="有几条今日计划，就复盘几条任务。" />
        <section v-if="todayPlan.tasks.length === 0" class="rounded-md border border-amber-200 bg-amber-50 p-5">先生成今日计划，再复盘。</section>
        <section v-else class="rounded-md border border-slate-200 bg-white p-5">
          <div class="grid gap-4 md:grid-cols-4">
            <input v-model="reviewForm.review_date" type="date" class="rounded-md border border-slate-300 px-3 py-2" />
            <input v-model.number="reviewForm.total_minutes" type="number" min="0" class="rounded-md border border-slate-300 px-3 py-2" placeholder="总分钟" />
            <select v-model="reviewForm.energy_level" class="rounded-md border border-slate-300 px-3 py-2">
              <option value="low">精力低</option>
              <option value="medium">精力普通</option>
              <option value="high">精力高</option>
            </select>
            <select v-model="reviewForm.focus_level" class="rounded-md border border-slate-300 px-3 py-2">
              <option>散</option>
              <option>普通</option>
              <option>稳</option>
            </select>
          </div>
          <article v-for="item in reviewForm.task_reviews" :key="item.task_id" class="mt-4 rounded-md border border-slate-200 p-4">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-xs font-semibold uppercase text-emerald-700">{{ taskById(item.task_id)?.module }}</p>
                <h3 class="font-semibold">{{ taskById(item.task_id)?.title }}</h3>
              </div>
              <select v-model="item.status" class="rounded-md border border-slate-300 px-3 py-2 text-sm">
                <option value="completed">完成</option>
                <option value="partial">部分完成</option>
                <option value="skipped">跳过</option>
              </select>
            </div>
            <div class="mt-4 grid gap-3 md:grid-cols-4">
              <input v-model.number="item.actual_minutes" type="number" class="rounded-md border border-slate-300 px-3 py-2" placeholder="分钟" />
              <select v-model="item.difficulty" class="rounded-md border border-slate-300 px-3 py-2">
                <option value="easy">轻松</option>
                <option value="normal">适中</option>
                <option value="hard">困难</option>
              </select>
              <select v-model.number="item.quality" class="rounded-md border border-slate-300 px-3 py-2">
                <option :value="1">1 没进入状态</option>
                <option :value="2">2 吃力</option>
                <option :value="3">3 普通</option>
                <option :value="4">4 有效</option>
                <option :value="5">5 很好</option>
              </select>
              <input v-model="item.next_action" class="rounded-md border border-slate-300 px-3 py-2" placeholder="明天怎么调" />
            </div>
            <div class="mt-3 grid gap-3 md:grid-cols-2">
              <textarea v-model="item.outcome" rows="2" class="rounded-md border border-slate-300 px-3 py-2" placeholder="完成了什么？" />
              <textarea v-model="item.blocker" rows="2" class="rounded-md border border-slate-300 px-3 py-2" placeholder="卡在哪里？" />
            </div>
          </article>
          <div class="mt-5 rounded-md bg-slate-50 p-4">
            <p class="text-sm font-semibold">导师参考维度</p>
            <p class="mt-1 text-xs text-slate-500">1=严重卡住，2=吃力，3=普通，4=顺，5=状态很好。</p>
            <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div v-for="item in reviewForm.dimensions" :key="item.dimension" class="rounded-md border border-slate-200 bg-white p-3">
                <div class="flex items-center justify-between">
                  <p class="text-sm font-semibold">{{ item.dimension }}</p>
                  <select v-model.number="item.score" class="rounded-md border border-slate-300 px-2 py-1 text-sm">
                    <option :value="1">1</option>
                    <option :value="2">2</option>
                    <option :value="3">3</option>
                    <option :value="4">4</option>
                    <option :value="5">5</option>
                  </select>
                </div>
                <input v-model="item.note" class="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="为什么？" />
              </div>
            </div>
          </div>
          <div class="mt-5 grid gap-4 md:grid-cols-2">
            <textarea v-model="reviewForm.wins" rows="3" class="rounded-md border border-slate-300 px-3 py-2" placeholder="今天的收获" />
            <textarea v-model="reviewForm.tomorrow_preference" rows="3" class="rounded-md border border-slate-300 px-3 py-2" placeholder="明天偏好" />
            <textarea v-model="reviewForm.hardest_part" rows="3" class="rounded-md border border-slate-300 px-3 py-2" placeholder="最难部分" />
            <textarea v-model="reviewForm.message_to_mentor" rows="3" class="rounded-md border border-slate-300 px-3 py-2" placeholder="想告诉导师的话" />
          </div>
          <button class="btn-primary mt-5" :disabled="isBusy" @click="submitReview">
            {{ busyAction === "review" ? "正在保存复盘，请勿重复提交" : "保存复盘并更新后台画像" }}
          </button>
        </section>
      </section>

      <section v-if="activeView === 'progress'" class="space-y-5">
        <Header title="学习进度" subtitle="从计划完成、任务质量、写作反馈和复盘维度里看趋势。" />
        <div class="grid gap-4 md:grid-cols-4">
          <Stat label="总学习分钟" :value="progress.total_minutes || 0" />
          <Stat label="复盘天数" :value="progress.study_days || 0" />
          <Stat label="连续记录" :value="progress.current_streak || 0" />
          <Stat label="完成率" :value="formatPercent(progress.completion_rate)" />
        </div>
        <Panel title="任务质量">
          <Metric v-for="item in progress.task_quality || []" :key="item.module" :title="item.module" :main="`${item.average_quality ?? '-'} / 5`" :sub="`完成 ${item.completed}/${item.reviews}，${item.minutes} 分钟`" />
        </Panel>
        <Panel title="维度趋势">
          <Metric v-for="item in progress.dimension_summary || []" :key="item.dimension" :title="item.dimension" :main="`${item.average ?? '-'} / 5`" :sub="item.latest_note" />
        </Panel>
      </section>

      <section v-if="activeView === 'reports'" class="space-y-5">
        <Header title="周/月报" subtitle="报告来自今日计划、任务级复盘、维度反馈和写作记录。" />
        <div class="grid gap-5 lg:grid-cols-2">
          <Report title="周报" :report="reports.weekly" />
          <Report title="月报" :report="reports.monthly" />
        </div>
      </section>

      <section v-if="activeView === 'settings'" class="space-y-5">
        <Header title="设置" subtitle="连接自己的大模型，并调整导师风格。长期记忆由后台自动沉淀。" />
        <section class="rounded-md border border-slate-200 bg-white p-5">
          <p class="text-sm text-slate-500">大模型连接</p>
          <p class="mt-1 text-lg font-semibold">{{ aiStatus.configured ? "已连接" : "未连接" }}</p>
          <p class="mt-1 text-sm text-slate-500">{{ aiStatus.base_url || "尚未配置接口地址" }} · {{ aiStatus.model || "尚未配置模型" }}</p>
          <button class="btn-secondary mt-4" :disabled="isBusy" @click="needsAiSetup = true">更新大模型连接</button>
        </section>
        <section class="rounded-md border border-slate-200 bg-white p-5">
          <label class="field-label">
            <span>导师风格</span>
            <select v-model="profile.mentor_style" class="field-control">
              <option value="warm_coach">温和但不糊弄</option>
              <option value="strict_coach">严格督促</option>
              <option value="analytical">理性规划</option>
              <option value="friend">朋友式陪伴</option>
            </select>
          </label>
          <div class="mt-4 grid gap-4 md:grid-cols-3">
            <label class="field-label">
              <span>目标分数</span>
              <input v-model.number="profile.target_band" type="number" step="0.5" class="field-control" />
            </label>
            <label class="field-label">
              <span>考试日期</span>
              <input v-model="profile.exam_date" type="date" class="field-control" />
            </label>
            <label class="field-label">
              <span>每天学习时间（分钟）</span>
              <input v-model.number="profile.daily_available_minutes" type="number" min="1" class="field-control" />
            </label>
          </div>
          <button class="btn-primary mt-4" :disabled="isBusy" @click="saveProfile">
            {{ busyAction === "profile" ? "正在保存，请勿重复提交" : "保存偏好" }}
          </button>
        </section>
      </section>
    </main>

    <div v-if="showOnboarding" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <section class="max-h-[92vh] w-full max-w-4xl overflow-auto rounded-md bg-white p-6 shadow-xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-emerald-700">入门对话</p>
            <h2 class="mt-1 text-2xl font-semibold">先让导师认识你</h2>
            <p class="mt-2 text-sm text-slate-500">保存后，导师会立刻起草今日大纲，并和你确认今天的真实状态。</p>
          </div>
          <button class="btn-secondary px-3 py-1.5" :disabled="isBusy" @click="closeOnboarding">关闭</button>
        </div>
        <p
          v-if="operationMessage"
          class="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800"
        >
          {{ operationMessage }}
        </p>
        <div class="mt-5 grid gap-4 md:grid-cols-3">
          <label class="field-label">
            <span>目标分数</span>
            <input v-model.number="onboardingForm.target_band" type="number" step="0.5" class="field-control" placeholder="例如 7.5" />
          </label>
          <label class="field-label">
            <span>考试日期</span>
            <input v-model="onboardingForm.exam_date" type="date" class="field-control" />
          </label>
          <label class="field-label">
            <span>每天学习时间（分钟）</span>
            <input v-model.number="onboardingForm.daily_available_minutes" type="number" min="1" class="field-control" placeholder="例如 120" />
          </label>
        </div>
        <div class="mt-4 grid gap-4 md:grid-cols-2">
          <label class="field-label">
            <span>想达到什么目标？</span>
            <textarea v-model="onboardingForm.goal_notes" rows="4" class="field-control" placeholder="例如：三个月后总分 7.5，写作至少 7。" />
          </label>
          <label class="field-label">
            <span>现在是什么基础？</span>
            <textarea v-model="onboardingForm.baseline_notes" rows="4" class="field-control" placeholder="例如：阅读还行，写作逻辑弱，口语容易卡。" />
          </label>
          <label class="field-label">
            <span>以前怎么学习？</span>
            <textarea v-model="onboardingForm.study_history" rows="4" class="field-control" placeholder="以前做过哪些练习、上过课或自学方式？" />
          </label>
          <label class="field-label">
            <span>哪些方法有效或无效？</span>
            <textarea v-model="onboardingForm.study_methods" rows="4" class="field-control" placeholder="比如背单词、精读、跟读、限时写作等。" />
          </label>
        </div>
        <label class="field-label mt-4">
          <span>希望导师怎么陪你学？</span>
          <textarea v-model="onboardingForm.learning_preferences" rows="3" class="field-control" placeholder="例如：温和但直接，不要空泛鼓励，最好给明确下一步。" />
        </label>
        <label class="field-label mt-4">
          <span>导师风格</span>
          <select v-model="onboardingForm.mentor_style" class="field-control">
            <option value="warm_coach">温和但不糊弄</option>
            <option value="strict_coach">严格督促</option>
            <option value="analytical">理性规划</option>
            <option value="friend">朋友式陪伴</option>
          </select>
        </label>
        <p v-if="busyAction === 'onboarding'" class="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
          正在保存画像并起草今日大纲，请勿重复提交。
        </p>
        <p v-else-if="!canSaveOnboarding" class="mt-4 text-sm text-slate-500">
          至少填写目标、当前基础和每天学习时间，导师才能开始起草计划。
        </p>
        <div class="mt-5 flex justify-end">
          <button class="btn-primary" :disabled="isBusy" @click="saveOnboarding">
            {{ busyAction === "onboarding" ? "正在保存并起草，请勿重复提交" : "保存画像并起草今日大纲" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref, watch } from "vue";
import { api } from "./api";

const navItems = [
  { id: "today", label: "今日计划" },
  { id: "writing", label: "写作批改" },
  { id: "review", label: "每日复盘" },
  { id: "progress", label: "学习进度" },
  { id: "reports", label: "周/月报" },
  { id: "settings", label: "设置" }
];
const fallbackDimensions = ["Listening", "Reading", "Writing", "Speaking", "Vocabulary", "Grammar", "Pronunciation", "Fluency", "Logic", "Test Strategy", "Focus", "Energy"];
const styleLabels = { warm_coach: "温和但不糊弄", strict_coach: "严格督促", analytical: "理性规划", friend: "朋友式陪伴" };

const activeView = ref("today");
const busyAction = ref("");
const operationMessage = ref("");
const statusMessage = ref("");
const showOnboarding = ref(false);
const needsAiSetup = ref(false);
const aiStatus = ref({ configured: false, provider: "openai-compatible", base_url: "", model: "" });
const aiConfig = ref({ provider: "openai-compatible", api_key: "", base_url: "", model: "", timeout_seconds: 25, max_tokens: 1600 });
const profile = ref({ target_band: 7.5, daily_available_minutes: 120, mentor_style: "warm_coach", onboarding_completed: false });
const onboardingForm = ref({});
const dimensions = ref(fallbackDimensions);
const todayPlan = ref({ needs_onboarding: true, plan: null, tasks: [] });
const progress = ref({ dimension_summary: [], task_quality: [] });
const reports = ref({ weekly: {}, monthly: {} });
const planDiscussion = ref(null);
const planFeedback = ref("");
const writingFeedback = ref(null);
const writingForm = ref({ task_type: "task2", prompt: "", essay_text: "" });
const reviewForm = ref(buildReviewForm(fallbackDimensions, []));

const todayLabel = computed(() => new Date().toLocaleDateString("zh-CN", { weekday: "long", year: "numeric", month: "long", day: "numeric" }));
const styleLabel = computed(() => styleLabels[profile.value.mentor_style] || "自定义导师");
const parsedWriting = computed(() => parseJson(writingFeedback.value?.feedback_json, writingFeedback.value?.feedback || {}));
const canSaveOnboarding = computed(() => Boolean(onboardingForm.value.goal_notes?.trim() && onboardingForm.value.baseline_notes?.trim() && Number(onboardingForm.value.daily_available_minutes || 0) > 0));
const canSaveAiConfig = computed(() => Boolean(aiConfig.value.api_key?.trim() && aiConfig.value.base_url?.trim() && aiConfig.value.model?.trim()));
const isBusy = computed(() => Boolean(busyAction.value));
const planQuestions = computed(() => planDiscussion.value?.questions_for_user || []);
const todayPlanTitle = computed(() => todayPlan.value.plan?.focus_summary || (planDiscussion.value ? "导师已经起草了今日大纲，等待你确认。" : "今天还没有计划。"));
const todayPlanReason = computed(() => todayPlan.value.plan?.ai_reason || (profile.value.onboarding_completed ? "导师会先和你确认今天的状态，再生成今日计划。" : "完成入门对话后，导师会根据画像起草今日大纲。"));
const discussionButtonLabel = computed(() => {
  if (busyAction.value === "plan-discussion") return "导师正在起草，请勿重复提交";
  if (todayPlan.value.plan) return "重新沟通今天安排";
  if (planDiscussion.value) return "刷新今日大纲";
  return "和导师聊今天";
});

watch(() => todayPlan.value.tasks, (tasks) => {
  reviewForm.value = buildReviewForm(dimensions.value, tasks || []);
}, { deep: true });

onMounted(refreshAll);

async function refreshAll() {
  aiStatus.value = await api.getAiStatus();
  aiConfig.value = {
    provider: aiStatus.value.provider || "openai-compatible",
    api_key: "",
    base_url: aiStatus.value.base_url || "",
    model: aiStatus.value.model || "",
    timeout_seconds: 25,
    max_tokens: 1600
  };
  needsAiSetup.value = !aiStatus.value.configured;
  if (needsAiSetup.value) {
    operationMessage.value = "请先连接你自己的大模型。开源版不会内置任何 API Key。";
    return;
  }

  const [loadedProfile, dimensionResult] = await Promise.all([api.getProfile(), api.getDimensions()]);
  profile.value = loadedProfile;
  onboardingForm.value = { ...loadedProfile };
  dimensions.value = dimensionResult.dimensions || fallbackDimensions;
  await Promise.all([loadTodayPlan(), loadProgress(), loadReports()]);
  if (!profile.value.onboarding_completed) {
    openOnboarding(true);
  } else if (!todayPlan.value.plan) {
    await preparePlanDiscussion({ auto: true });
  }
}

async function saveAiConfig() {
  if (!canSaveAiConfig.value) {
    operationMessage.value = "请填写接口地址、模型名称和 API Key。";
    return;
  }
  await runWithBusy("ai-config", "正在测试并保存大模型连接...", async () => {
    aiStatus.value = await api.updateAiConfig(aiConfig.value);
    needsAiSetup.value = !aiStatus.value.configured;
    if (!aiStatus.value.configured) {
      throw new Error("配置没有保存成功，请检查接口地址、模型名称和 API Key。");
    }
    await refreshAll();
  }, "大模型连接测试通过，配置已保存。");
}

async function testAiConfig() {
  if (!canSaveAiConfig.value) {
    operationMessage.value = "请填写接口地址、模型名称和 API Key。";
    return;
  }
  await runWithBusy("ai-test", "正在测试大模型连接...", async () => {
    await api.testAiConfig(aiConfig.value);
  }, "大模型连接测试通过。");
}

async function loadTodayPlan() {
  todayPlan.value = await api.getTodayPlan();
  if (!Object.prototype.hasOwnProperty.call(todayPlan.value, "needs_onboarding")) {
    operationMessage.value = "检测到当前 8000 后端仍是旧版本，请重新运行启动脚本，让它替换旧后端进程。";
  }
  reviewForm.value = buildReviewForm(dimensions.value, todayPlan.value.tasks || []);
}

async function loadProgress() {
  progress.value = await api.getProgress();
}

async function loadReports() {
  reports.value = await api.getReports();
}

function openOnboarding(force = false) {
  if (isBusy.value && !force) {
    operationMessage.value = "上一项还在执行，请稍候。";
    return;
  }
  onboardingForm.value = { ...profile.value };
  showOnboarding.value = true;
  operationMessage.value = profile.value.onboarding_completed ? "可以更新你的入门画像。" : "请先完成入门对话，保存后导师会自动起草今日大纲。";
}

function closeOnboarding() {
  showOnboarding.value = false;
  if (!profile.value.onboarding_completed) {
    operationMessage.value = "你可以先关闭看看，但生成今日计划前仍需要完成入门对话。";
  }
}

async function runWithBusy(action, message, work, doneMessage = "") {
  if (isBusy.value) {
    operationMessage.value = "上一项还在执行，请勿重复提交。";
    return null;
  }
  busyAction.value = action;
  operationMessage.value = message;
  try {
    const result = await work();
    if (doneMessage) operationMessage.value = doneMessage;
    return result;
  } catch (error) {
    console.error(error);
    operationMessage.value = readableError(error);
    return null;
  } finally {
    busyAction.value = "";
  }
}

async function saveOnboarding() {
  if (!canSaveOnboarding.value) {
    operationMessage.value = "请先填写目标、当前基础和每天学习时间，再保存画像。";
    return;
  }
  await runWithBusy("onboarding", "正在保存画像并起草今日大纲，请勿重复提交。", async () => {
    const summary = [
      `目标：${onboardingForm.value.goal_notes}`,
      `基础：${onboardingForm.value.baseline_notes}`,
      `学习经历：${onboardingForm.value.study_history || "未填写"}`,
      `方法偏好：${onboardingForm.value.study_methods || "未填写"}`,
      `导师偏好：${onboardingForm.value.learning_preferences || "未填写"}`
    ].join("\n");
    profile.value = await api.updateProfile({ ...onboardingForm.value, onboarding_completed: true, onboarding_summary: summary, current_level_notes: summary });
    if (!profile.value.onboarding_completed) {
      throw new Error("后端没有保存入门完成状态。当前 8000 端口可能仍是旧后端，请重新运行启动脚本。");
    }
    showOnboarding.value = false;
    activeView.value = "today";
    await Promise.all([loadTodayPlan(), loadProgress(), loadReports()]);
    const result = await api.getPlanDiscussion();
    planDiscussion.value = result.discussion?.needs_onboarding ? null : result.discussion;
    planFeedback.value = "";
    statusMessage.value = "导师已认识你，并起草了今天的大纲。请补充今天状态后生成计划。";
  }, "画像已保存，导师已起草今日大纲。");
}

async function preparePlanDiscussion({ auto = false } = {}) {
  if (!profile.value.onboarding_completed) {
    openOnboarding();
    return;
  }
  await runWithBusy("plan-discussion", auto ? "导师正在根据最近记录起草今日大纲，请勿重复提交。" : "导师正在分析你的画像和最近数据，请勿重复提交。", async () => {
    const result = await api.getPlanDiscussion();
    if (result.discussion?.needs_onboarding) {
      openOnboarding(true);
      return;
    }
    planDiscussion.value = result.discussion;
    planFeedback.value = "";
    statusMessage.value = "导师已起草今日大纲，请先确认今天真实状态。";
    activeView.value = "today";
  }, auto ? "已进入今日沟通，确认后即可生成计划。" : "已生成今日沟通大纲。");
}

async function startPlanDiscussion() {
  await preparePlanDiscussion();
}

async function generatePlan() {
  if (!profile.value.onboarding_completed) {
    openOnboarding();
    return;
  }
  await runWithBusy("generate-plan", "正在生成今日计划，请勿重复提交。", async () => {
    todayPlan.value = await api.generatePlan();
    if (todayPlan.value.needs_onboarding) {
      openOnboarding(true);
      return;
    }
    planDiscussion.value = null;
    statusMessage.value = "今日计划已生成。";
    await Promise.all([loadProgress(), loadReports()]);
  }, "今日计划已生成。");
}

async function regeneratePlan() {
  await runWithBusy("regenerate-plan", "正在根据补充重新生成，请勿重复提交。", async () => {
    todayPlan.value = await api.regeneratePlan({ user_feedback: planFeedback.value });
    planDiscussion.value = null;
    statusMessage.value = "导师已根据你的补充生成今日计划。";
    await Promise.all([loadProgress(), loadReports()]);
  }, "导师已根据你的补充生成今日计划。");
}

async function loadNextPrompt() {
  operationMessage.value = "开源版不内置练习题，请直接粘贴你自己的题目或作文。";
}

async function submitWriting() {
  await runWithBusy("writing", "导师正在批改，请勿重复提交。", async () => {
    writingFeedback.value = await api.reviewWriting(writingForm.value);
    await Promise.all([loadProgress(), loadReports()]);
  }, "写作反馈已保存，并会进入后续计划和复盘。");
}

async function submitReview() {
  await runWithBusy("review", "正在保存复盘并更新后台画像，请勿重复提交。", async () => {
    reviewForm.value.total_minutes = reviewForm.value.task_reviews.reduce((sum, item) => sum + Number(item.actual_minutes || 0), 0) || reviewForm.value.total_minutes;
    const saved = await api.submitDailyReview({ ...reviewForm.value, plan_id: todayPlan.value.plan?.id || null });
    statusMessage.value = saved.summary?.coach_note || "复盘已保存。";
    await Promise.all([loadTodayPlan(), loadProgress(), loadReports()]);
    activeView.value = "progress";
  }, "复盘已保存，学习进度和周/月报已更新。");
}

async function saveProfile() {
  await runWithBusy("profile", "正在保存导师偏好，请勿重复提交。", async () => {
    profile.value = await api.updateProfile(profile.value);
    statusMessage.value = "导师偏好已保存。";
  }, "导师偏好已保存。");
}

function buildReviewForm(sourceDimensions, tasks) {
  return {
    review_date: new Date().toISOString().slice(0, 10),
    plan_id: todayPlan.value?.plan?.id || null,
    total_minutes: 0,
    energy_level: "medium",
    mood: "",
    focus_level: "普通",
    completion_level: "中",
    hardest_part: "",
    unfinished_reason: "",
    task_reviews: tasks.map((task) => ({
      task_id: task.id,
      status: "completed",
      actual_minutes: task.actual_minutes || task.estimated_minutes || 0,
      difficulty: task.difficulty || "normal",
      quality: 3,
      outcome: "",
      blocker: "",
      next_action: ""
    })),
    dimensions: sourceDimensions.map((dimension) => ({ dimension, score: 3, note: "" })),
    module_reflections: [],
    blockers: [],
    wins: "",
    tomorrow_preference: "",
    message_to_mentor: ""
  };
}

function taskById(id) {
  return todayPlan.value.tasks.find((task) => task.id === id);
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function parseJson(value, fallback = {}) {
  if (!value) return fallback;
  if (typeof value === "object") return value;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function readableError(error) {
  if (error?.status) {
    const body = error.body ? `：${String(error.body).slice(0, 160)}` : "";
    return `后端返回错误 ${error.status}${body}`;
  }
  if (error?.message) return error.message;
  return "刚才没有执行成功，请确认后端已启动，或稍后重试。";
}

const Header = defineComponent({
  props: { title: String, subtitle: String },
  setup: (props) => () => h("header", {}, [
    h("h2", { class: "text-3xl font-semibold" }, props.title),
    h("p", { class: "mt-2 text-sm text-slate-500" }, props.subtitle)
  ])
});

const Info = defineComponent({
  props: { title: String, text: String },
  setup: (props) => () => h("div", { class: "rounded-md bg-slate-50 p-4" }, [
    h("p", { class: "text-sm font-semibold" }, props.title),
    h("p", { class: "mt-2 text-sm leading-6 text-slate-600" }, props.text || "-")
  ])
});

const Stat = defineComponent({
  props: { label: String, value: [String, Number] },
  setup: (props) => () => h("div", { class: "rounded-md border border-slate-200 bg-white p-5" }, [
    h("p", { class: "text-sm text-slate-500" }, props.label),
    h("p", { class: "mt-2 text-3xl font-semibold" }, String(props.value))
  ])
});

const Panel = defineComponent({
  props: { title: String },
  setup: (props, { slots }) => () => h("section", { class: "rounded-md border border-slate-200 bg-white p-5" }, [
    h("p", { class: "text-sm font-medium text-slate-500" }, props.title),
    h("div", { class: "mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3" }, slots.default?.())
  ])
});

const Metric = defineComponent({
  props: { title: String, main: String, sub: String },
  setup: (props) => () => h("div", { class: "rounded-md bg-slate-50 p-3" }, [
    h("div", { class: "flex items-center justify-between text-sm" }, [
      h("span", { class: "font-semibold" }, props.title),
      h("span", {}, props.main)
    ]),
    props.sub ? h("p", { class: "mt-2 text-xs text-slate-500" }, props.sub) : null
  ])
});

function reportPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function reportLowDimensions(report) {
  return (report?.low_dimensions || report?.dimension_averages || [])
    .filter((item) => item.average !== null && item.average !== undefined)
    .sort((a, b) => Number(a.average) - Number(b.average))
    .slice(0, 4);
}

function reportRisks(report) {
  const blockers = (report?.task_module_report || [])
    .filter((item) => item.latest_blocker)
    .map((item) => ({ title: item.module, text: item.latest_blocker }));
  const weaknesses = (report?.top_weaknesses || [])
    .map((item) => ({ title: item.category || "风险", text: item.description || item.evidence }));
  return [...blockers, ...weaknesses].slice(0, 4);
}

function reportEnergy(report) {
  return (report?.energy_focus || []).slice(-5).reverse();
}

function reportBand(value) {
  return value ? `Band ${value}` : "-";
}

const Report = defineComponent({
  props: { title: String, report: Object },
  setup: (props) => () => {
    const report = props.report || {};
    const modules = report.task_module_report || [];
    const lowDimensions = reportLowDimensions(report);
    const risks = reportRisks(report);
    const energyRows = reportEnergy(report);
    return h("section", { class: "rounded-md border border-slate-200 bg-white p-5" }, [
      h("div", { class: "flex items-start justify-between gap-4" }, [
        h("div", {}, [
          h("p", { class: "text-sm text-slate-500" }, props.title),
          h("p", { class: "mt-2 text-2xl font-semibold" }, `${report.total_minutes || 0} 分钟`)
        ]),
        h("span", { class: "rounded-md bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700" }, `完成率 ${reportPercent(report.completion_rate)}`)
      ]),
      h("p", { class: "mt-3 text-sm leading-6 text-slate-600" }, report.mentor_summary || "还没有足够数据生成报告。"),
      h("div", { class: "mt-4 grid gap-3 sm:grid-cols-2" }, [
        h("div", { class: "rounded-md bg-slate-50 p-3" }, [
          h("p", { class: "text-xs text-slate-500" }, "计划任务"),
          h("p", { class: "mt-1 text-lg font-semibold" }, `${report.reviewed_task_count || 0}/${report.planned_task_count || 0}`),
          h("p", { class: "text-xs text-slate-500" }, `复盘覆盖 ${reportPercent(report.review_rate)}`)
        ]),
        h("div", { class: "rounded-md bg-slate-50 p-3" }, [
          h("p", { class: "text-xs text-slate-500" }, "写作反馈"),
          h("p", { class: "mt-1 text-lg font-semibold" }, `${report.writing_count || 0} 次`),
          h("p", { class: "text-xs text-slate-500" }, `均分 ${reportBand(report.writing_average_band)}`)
        ]),
        h("div", { class: "rounded-md bg-slate-50 p-3" }, [
          h("p", { class: "text-xs text-slate-500" }, "复盘天数"),
          h("p", { class: "mt-1 text-lg font-semibold" }, `${report.study_days || 0} 天`),
          h("p", { class: "text-xs text-slate-500" }, `计划天数 ${report.planned_days || 0}`)
        ]),
        h("div", { class: "rounded-md bg-slate-50 p-3" }, [
          h("p", { class: "text-xs text-slate-500" }, "未复盘任务"),
          h("p", { class: "mt-1 text-lg font-semibold" }, `${report.unreviewed_task_count || 0}`),
          h("p", { class: "text-xs text-slate-500" }, "用来判断执行闭环")
        ])
      ]),
      h("p", { class: "mt-5 text-sm font-semibold" }, "计划和复盘"),
      modules.length ? h("div", { class: "mt-3 space-y-2" }, modules.slice(0, 6).map((item) => h("div", { class: "rounded-md border border-slate-100 bg-slate-50 p-3 text-sm" }, [
        h("div", { class: "flex items-center justify-between gap-3" }, [
          h("span", { class: "font-semibold" }, item.module),
          h("span", {}, `完成 ${item.completed_count || 0}/${item.planned_count || 0}`)
        ]),
        h("p", { class: "mt-1 text-xs text-slate-500" }, `复盘 ${item.reviewed_count || 0} 条，实际 ${item.actual_minutes ?? item.minutes ?? 0} 分钟，质量 ${item.average_quality ?? "-"}/5`),
        item.latest_blocker ? h("p", { class: "mt-2 text-xs text-amber-700" }, `阻碍：${item.latest_blocker}`) : null
      ]))) : h("p", { class: "mt-2 rounded-md bg-slate-50 p-3 text-sm text-slate-500" }, "还没有计划任务或复盘任务。"),
      h("p", { class: "mt-5 text-sm font-semibold" }, "低信号维度"),
      lowDimensions.length ? h("div", { class: "mt-3 grid gap-2 sm:grid-cols-2" }, lowDimensions.map((item) => h("div", { class: "rounded-md bg-amber-50 p-3 text-sm text-amber-900" }, `${item.dimension}: ${item.average}/5${item.latest_note ? `，${item.latest_note}` : ""}`))) : h("p", { class: "mt-2 rounded-md bg-slate-50 p-3 text-sm text-slate-500" }, "维度数据还不够，先完成几天每日复盘。"),
      h("p", { class: "mt-5 text-sm font-semibold" }, "精力和专注"),
      energyRows.length ? h("div", { class: "mt-3 space-y-2" }, energyRows.map((item) => h("div", { class: "flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm" }, [
        h("span", {}, item.review_date),
        h("span", { class: "text-slate-600" }, `精力 ${item.energy_level || "-"} / 专注 ${item.focus_level || "-"}`)
      ]))) : h("p", { class: "mt-2 rounded-md bg-slate-50 p-3 text-sm text-slate-500" }, "暂无精力和专注趋势。"),
      risks.length ? h("div", { class: "mt-5 rounded-md border border-amber-200 bg-amber-50 p-3" }, [
        h("p", { class: "text-sm font-semibold text-amber-900" }, "风险和阻碍"),
        ...risks.map((item) => h("p", { class: "mt-2 text-sm text-amber-900" }, `${item.title}: ${item.text}`))
      ]) : null,
      h("p", { class: "mt-5 text-sm font-semibold" }, "下一步"),
      h("p", { class: "mt-1 text-sm leading-6 text-slate-600" }, report.next_focus || "继续积累计划和复盘数据。")
    ]);
  }
});
</script>

<style scoped>
.btn-primary {
  border-radius: 0.375rem;
  background: #047857;
  color: white;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 700;
}

.btn-secondary {
  border: 1px solid #cbd5e1;
  border-radius: 0.375rem;
  background: white;
  color: #0f172a;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 700;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.field-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #334155;
}

.field-label > span {
  display: block;
  margin-bottom: 0.375rem;
}

.field-control {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 400;
  color: #0f172a;
}
</style>
