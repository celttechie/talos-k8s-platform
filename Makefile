# ==============================================================================
# Talos Kubernetes Platform Infrastructure Automation Makefile
# ==============================================================================
# Provides standard developer workflows, multi-stage lifecycle commands,
# verification tooling, environment diagnostics, and quality gates.
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Paths
STAGE1_DIR  := terraform/environments/01-nested-sandbox
STAGE2_DIR  := terraform/environments/02-talos-cluster
TALOS_DIR   := talos
GITOPS_DIR  := gitops
SCRIPTS_DIR := scripts

# Colors
BLUE   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

##@ 📖 Help & Diagnostics

.PHONY: help
help: ## Display this interactive help menu
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@echo -e "$(BLUE)     Talos Kubernetes Platform Infrastructure Automation Targets              $(RESET)"
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

.PHONY: doctor
doctor: ## Audit local workstation prerequisites, binaries, and configurations
	@python3 $(SCRIPTS_DIR)/doctor.py

##@ 🏗️ Stage 1: Nested Sandbox Hypervisor (01-nested-sandbox)

.PHONY: stage1-init
stage1-init: ## Initialize Terraform providers for Stage 1
	@echo -e "$(GREEN)===> Initializing Stage 1 Nested Sandbox workspace...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) init

.PHONY: stage1-plan
stage1-plan: ## Generate and review execution plan for Stage 1
	@echo -e "$(GREEN)===> Planning Stage 1 Nested Sandbox infrastructure...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) plan

.PHONY: stage1-apply
stage1-apply: ## Provision Stage 1 Nested Sandbox VM hypervisor
	@echo -e "$(GREEN)===> Applying Stage 1 Nested Sandbox infrastructure...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) apply

.PHONY: stage1-destroy
stage1-destroy: ## Destroy Stage 1 Nested Sandbox infrastructure
	@echo -e "$(YELLOW)===> Destroying Stage 1 Nested Sandbox infrastructure...$(RESET)"
	terraform -chdir=$(STAGE1_DIR) destroy

##@ 🚀 Stage 2: Talos Downstream Cluster (02-talos-cluster)

.PHONY: stage2-init
stage2-init: ## Initialize Terraform providers for Stage 2
	@echo -e "$(GREEN)===> Initializing Stage 2 Talos Cluster workspace...$(RESET)"
	terraform -chdir=$(STAGE2_DIR) init

.PHONY: stage2-plan
stage2-plan: ## Generate and review execution plan for Stage 2
	@echo -e "$(GREEN)===> Planning Stage 2 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE2_DIR) plan

.PHONY: stage2-apply
stage2-apply: ## Provision Stage 2 Talos Control Plane & Worker VMs
	@echo -e "$(GREEN)===> Applying Stage 2 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE2_DIR) apply

.PHONY: stage2-destroy
stage2-destroy: ## Destroy Stage 2 Talos Cluster infrastructure
	@echo -e "$(YELLOW)===> Destroying Stage 2 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE2_DIR) destroy

##@ ⚙️ Stage 3: Talos OS & Kubernetes Bootstrapping

.PHONY: talos-gen-config
talos-gen-config: ## Generate declarative Talos machine configurations with patches
	@echo -e "$(GREEN)===> Generating Talos machine configurations...$(RESET)"
	@bash $(SCRIPTS_DIR)/generate_talos_config.sh

.PHONY: talos-bootstrap
talos-bootstrap: ## Bootstrap etcd and initialize upstream control plane
	@echo -e "$(GREEN)===> Bootstrapping Talos Kubernetes control plane...$(RESET)"
	talosctl --talosconfig $(TALOS_DIR)/talosconfig bootstrap

.PHONY: talos-kubeconfig
talos-kubeconfig: ## Extract admin kubeconfig from Talos control plane
	@echo -e "$(GREEN)===> Extracting admin kubeconfig...$(RESET)"
	talosctl --talosconfig $(TALOS_DIR)/talosconfig kubeconfig ./kubeconfig
	@echo -e "$(GREEN)Admin kubeconfig written to ./kubeconfig$(RESET)"

.PHONY: talos-health
talos-health: ## Verify health of etcd, control plane components, and nodes
	@echo -e "$(GREEN)===> Auditing Talos cluster health...$(RESET)"
	talosctl --talosconfig $(TALOS_DIR)/talosconfig health

##@ 🌐 Stage 4: Platform Services (Cilium CNI & Longhorn CSI)

.PHONY: cilium-install
cilium-install: ## Deploy Cilium CNI with eBPF kube-proxy replacement
	@echo -e "$(GREEN)===> Deploying Cilium CNI via Helm...$(RESET)"
	helm upgrade --install cilium cilium/cilium --version 1.16.1 \
		--namespace kube-system \
		-f $(GITOPS_DIR)/platform/cilium/values.yaml

.PHONY: cilium-verify
cilium-verify: ## Run automated connectivity & eBPF flow tests
	@echo -e "$(GREEN)===> Running Cilium connectivity validation suite...$(RESET)"
	cilium connectivity test

.PHONY: longhorn-install
longhorn-install: ## Deploy Longhorn distributed block storage
	@echo -e "$(GREEN)===> Deploying Longhorn CSI storage engine...$(RESET)"
	helm upgrade --install longhorn longhorn/longhorn --version 1.7.1 \
		--namespace longhorn-system --create-namespace \
		-f $(GITOPS_DIR)/platform/longhorn/values.yaml

##@ 🔄 Stage 5: GitOps Delivery (ArgoCD & Workloads)

.PHONY: gitops-bootstrap
gitops-bootstrap: ## Apply ArgoCD Root Application (App-of-Apps)
	@echo -e "$(GREEN)===> Bootstrapping ArgoCD Root App-of-Apps...$(RESET)"
	kubectl apply -f $(GITOPS_DIR)/bootstrap/root-application.yaml

##@ 🧹 Code Quality, Linting & Pre-commit

.PHONY: lint
lint: ## Run all pre-commit quality gates and linter checks
	@echo -e "$(GREEN)===> Running pre-commit validation suite...$(RESET)"
	pre-commit run --all-files

.PHONY: fmt
fmt: ## Automatically format Terraform files
	@echo -e "$(GREEN)===> Formatting Terraform manifests...$(RESET)"
	terraform fmt -recursive

.PHONY: clean
clean: ## Clean up temporary files, caches, and test artifacts
	@echo -e "$(YELLOW)===> Cleaning temporary and build artifacts...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".terraform.tfstate.lock.info" -delete 2>/dev/null || true
	@echo -e "$(GREEN)Clean complete.$(RESET)"
