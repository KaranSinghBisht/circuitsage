"""CircuitSage Gemma 3 4B LoRA — Unsloth Kaggle template recipe (attempt v9).

This is the script form of the Kaggle notebook. It is structured so each top-level
section can be pasted into a separate cell of Unsloth's official "Gemma 3 (4B)
Conversational" Kaggle template, which pins a known-good torch + CUDA + bitsandbytes
stack (the missing ingredient that killed v1-v8 of our prior attempts).

Recommended workflow:
1. Open https://www.kaggle.com/code/danielhanchen/gemma-3-4b-conversational-finetune
   (or the latest Unsloth Gemma 3 template — search "Unsloth Gemma 3 conversational"
   in Kaggle Code if that URL has rotated).
2. Click "Copy & Edit". This forks the template into your account with the right
   environment image. DO NOT change the install cell.
3. Replace the dataset / model / training / export cells with the sections below
   (each marked `# ===== SECTION N =====`).
4. Add the dataset `karansinghbisht/circuitsage-faults-v1` from the right rail.
5. Run all cells. Expected wall-clock on Kaggle T4: ~60-90 minutes.
6. Download `/kaggle/working/gguf/circuitsage-lora-q4_k_m.gguf` and the Modelfile.
7. Locally: `ollama create circuitsage:latest -f circuitsage.Modelfile`.
   The CircuitSage backend auto-prefers `circuitsage:latest` over `gemma3:4b`
   when present (see `backend/app/config.py:_default_ollama_model`).

Why this works after 8 failures: prior attempts pinned bleeding-edge versions of
unsloth/triton/bitsandbytes against Kaggle's stale torch image. Forking Unsloth's
official Kaggle template inverts the dependency direction — we get their tested
stack and only contribute data + hyperparameters.
"""

# ===== SECTION 1: keep the template's install cell untouched =====
# (Do not edit; Unsloth's template handles torch / triton / bitsandbytes pinning.)


# ===== SECTION 2: imports + config =====
import json
import os
from pathlib import Path

import torch
from datasets import load_dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template, standardize_sharegpt


MODEL_ID = "unsloth/gemma-3-4b-it-unsloth-bnb-4bit"
MAX_SEQ_LENGTH = 4096
LORA_RANK = 16
LORA_ALPHA = 32
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
BATCH_SIZE = 2
GRAD_ACCUM = 4

DATASET_PATH = "/kaggle/input/circuitsage-faults-v1/circuitsage_qa.jsonl"
WORKING = Path("/kaggle/working")
ADAPTER_DIR = WORKING / "circuitsage-lora"
GGUF_DIR = WORKING / "gguf"
ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
GGUF_DIR.mkdir(parents=True, exist_ok=True)

print("torch:", torch.__version__, "cuda:", torch.cuda.is_available())
assert torch.cuda.is_available(), "Kaggle GPU not detected — check 'Accelerator: GPU T4 x2' in the kernel sidebar."


# ===== SECTION 3: load model + attach LoRA adapter =====
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_ID,
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=True,
    full_finetuning=False,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_RANK,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_alpha=LORA_ALPHA,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

tokenizer = get_chat_template(tokenizer, chat_template="gemma3")


# ===== SECTION 4: load dataset =====
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
dataset = standardize_sharegpt(dataset)


def formatting_prompts_func(examples):
    convos = examples["messages"]
    texts = [
        tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False)
        for convo in convos
    ]
    return {"text": texts}


dataset = dataset.map(formatting_prompts_func, batched=True)
print("dataset rows:", len(dataset))
print("sample text:", dataset[0]["text"][:600])


# ===== SECTION 5: train =====
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    args=SFTConfig(
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_steps=20,
        num_train_epochs=NUM_EPOCHS,
        learning_rate=LEARNING_RATE,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir=str(WORKING / "checkpoints"),
        save_strategy="epoch",
        report_to="none",
    ),
)

trainer_stats = trainer.train()
print("Training stats:", trainer_stats)


# ===== SECTION 6: save adapter + export GGUF + write Modelfile =====
model.save_pretrained(str(ADAPTER_DIR))
tokenizer.save_pretrained(str(ADAPTER_DIR))
print("Adapter saved to", ADAPTER_DIR)

model.save_pretrained_gguf(
    str(GGUF_DIR),
    tokenizer,
    quantization_method="q4_k_m",
)
gguf_files = list(GGUF_DIR.glob("*.gguf"))
print("GGUF files:", gguf_files)

modelfile_text = """FROM ./circuitsage-lora-q4_k_m.gguf
TEMPLATE \"\"\"{{ .System }}
{{ .Prompt }}\"\"\"
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
SYSTEM \"\"\"You are CircuitSage, an offline electronics lab partner. Return strict JSON when the user asks for structured diagnosis.\"\"\"
"""
(GGUF_DIR / "circuitsage.Modelfile").write_text(modelfile_text)
print("Modelfile written. Download both files from the kernel output panel.")


# ===== SECTION 7 (optional): quick sanity inference =====
FastLanguageModel.for_inference(model)
test_prompt = tokenizer.apply_chat_template(
    [
        {"role": "system", "content": "You are CircuitSage, an electronics lab partner."},
        {
            "role": "user",
            "content": (
                "I built an inverting op-amp with TL081, gain expected -4.7, but Vout is "
                "stuck near +12 V. What measurement should I take next? Return strict JSON."
            ),
        },
    ],
    tokenize=False,
    add_generation_prompt=True,
)
inputs = tokenizer(test_prompt, return_tensors="pt").to("cuda")
output = model.generate(**inputs, max_new_tokens=256, temperature=0.3)
print(tokenizer.decode(output[0], skip_special_tokens=True))
