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

-include target.env

# Colors
BLUE   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

##@ 📖 Setup, Diagnostics & Quality Gates

.PHONY: help
help: ## Display this interactive help menu
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@echo -e "$(BLUE)     Talos Kubernetes Platform Infrastructure Automation Targets              $(RESET)"
	@echo -e "$(BLUE)==============================================================================$(RESET)"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

.PHONY: configure
configure: ## Interactive wizard to define, verify, and persist target deployment server
	@python3 $(SCRIPTS_DIR)/configure.py

TARGET_HOST ?= $(if $(TARGET_HOST),$(TARGET_HOST),t5600)

.PHONY: doctor
doctor: ## Audit local workstation developer tools, CLI binaries, and git hooks
	@python3 $(SCRIPTS_DIR)/doctor.py

.PHONY: preflight
preflight: ## Validate target hypervisor server (KVM, libvirtd, storage pools, bridges)
	@python3 $(SCRIPTS_DIR)/preflight_server.py --host $(TARGET_HOST)

.PHONY: check-all
check-all: ## Execute both workstation doctor and target server preflight audits
	@$(MAKE) doctor
	@$(MAKE) preflight

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

.PHONY: verify-stage1
verify-stage1: ## Run automated verification checks on Stage 1 sandbox hypervisor
	@echo -e "$(GREEN)===> Running Stage 1 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage1.py

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

.PHONY: verify-stage2
verify-stage2: ## Run automated verification checks on Stage 2 Talos VMs
	@echo -e "$(GREEN)===> Running Stage 2 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage2.py

.PHONY: stage2-destroy
stage2-destroy: ## Destroy Stage 2 Talos Cluster infrastructure
	@echo -e "$(YELLOW)===> Destroying Stage 2 Talos Cluster infrastructure...$(RESET)"
	terraform -chdir=$(STAGE2_DIR) destroy

.PHONY: test-m1
test-m1: ## Execute full Milestone 1 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 1 Test Suite...$(RESET)"
	@$(MAKE) fmt
	@$(MAKE) verify-stage1
	@$(MAKE) verify-stage2

##@ ⚙️ Stage 3: Talos OS & Kubernetes Bootstrapping

.PHONY: talos-gen-config
talos-gen-config: ## Generate declarative Talos machine configurations with patches
	@echo -e "$(GREEN)===> Generating Talos machine configurations...$(RESET)"
	@bash $(SCRIPTS_DIR)/generate_talos_config.sh

.PHONY: talos-apply-config
talos-apply-config: ## Apply declarative machine configs to Control Plane & Worker nodes
	@echo -e "$(GREEN)===> Applying Talos machine configurations...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --apply-only

.PHONY: talos-bootstrap
talos-bootstrap: ## Bootstrap etcd quorum and initialize upstream control plane
	@echo -e "$(GREEN)===> Bootstrapping Talos Kubernetes control plane...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --bootstrap-only

.PHONY: talos-kubeconfig
talos-kubeconfig: ## Extract admin kubeconfig from Talos control plane
	@echo -e "$(GREEN)===> Extracting admin kubeconfig...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --kubeconfig-only

.PHONY: talos-health
talos-health: ## Verify health of etcd, control plane components, and nodes
	@echo -e "$(GREEN)===> Auditing Talos cluster health...$(RESET)"
	@python3 $(SCRIPTS_DIR)/bootstrap_cluster.py --health-only

.PHONY: verify-stage3
verify-stage3: ## Run automated verification checks on Stage 3 Talos bootstrapping
	@echo -e "$(GREEN)===> Running Stage 3 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage3.py

.PHONY: test-m2
test-m2: ## Execute full Milestone 2 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 2 Test Suite...$(RESET)"
	@$(MAKE) talos-gen-config
	@$(MAKE) verify-stage3


##@ 🌐 Stage 4: Platform Services (Cilium CNI & Longhorn CSI)

.PHONY: cilium-install
cilium-install: ## Deploy Cilium CNI with eBPF kube-proxy replacement and L2 policies
	@echo -e "$(GREEN)===> Deploying Cilium CNI via Helm...$(RESET)"
	helm repo add cilium https://helm.cilium.io/ 2>/dev/null || true
	helm repo update cilium
	helm upgrade --install cilium cilium/cilium --version 1.16.1 \
		--namespace kube-system \
		-f $(GITOPS_DIR)/platform/cilium/values.yaml
	@echo -e "$(GREEN)===> Applying Cilium L2 Announcement Policy & IP Pool...$(RESET)"
	kubectl apply -f $(GITOPS_DIR)/platform/cilium/l2-policy.yaml

.PHONY: cilium-verify
cilium-verify: ## Run automated connectivity & eBPF flow tests
	@echo -e "$(GREEN)===> Running Cilium connectivity validation suite...$(RESET)"
	cilium connectivity test

.PHONY: longhorn-install
longhorn-install: ## Deploy Longhorn distributed block storage
	@echo -e "$(GREEN)===> Deploying Longhorn CSI storage engine...$(RESET)"
	helm repo add longhorn https://charts.longhorn.io 2>/dev/null || true
	helm repo update longhorn
	helm upgrade --install longhorn longhorn/longhorn --version 1.7.1 \
		--namespace longhorn-system --create-namespace \
		-f $(GITOPS_DIR)/platform/longhorn/values.yaml

.PHONY: verify-stage4
verify-stage4: ## Run automated verification checks on Stage 4 Cilium and Longhorn
	@echo -e "$(GREEN)===> Running Stage 4 verification test suite...$(RESET)"
	@python3 $(SCRIPTS_DIR)/verify_stage4.py

.PHONY: test-m3
test-m3: ## Execute full Milestone 3 validation and verification test suite
	@echo -e "$(GREEN)===> Running Milestone 3 Test Suite...$(RESET)"
	@$(MAKE) verify-stage4


##@ 📊 Observability & Monitoring (Prometheus, Grafana & Hubble)

.PHONY: monitoring-install
monitoring-install: ## Deploy kube-prometheus-stack (Prometheus & Grafana)
	@echo -e "$(GREEN)===> Deploying kube-prometheus-stack...$(RESET)"
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo update prometheus-community
	helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
		--namespace monitoring --create-namespace \
		-f $(GITOPS_DIR)/platform/monitoring/kube-prometheus-stack.yaml

.PHONY: hubble-ui
hubble-ui: ## Port-forward and open Cilium Hubble UI (http://localhost:12000)
	@echo -e "$(GREEN)===> Port-forwarding Hubble UI to http://localhost:12000...$(RESET)"
	cilium hubble ui --port 12000

.PHONY: grafana
grafana: ## Port-forward Grafana dashboard to http://localhost:3000 (admin / prom-operator)
	@echo -e "$(GREEN)===> Port-forwarding Grafana to http://localhost:3000...$(RESET)"
	kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

##@ 🧪 Training Workload & Troubleshooting Drills

.PHONY: workload-install
workload-install: ## Deploy multi-tier communicating training application
	@echo -e "$(GREEN)===> Deploying training workload microservices...$(RESET)"
	kubectl apply -k $(GITOPS_DIR)/apps/training-app

.PHONY: workload-destroy
workload-destroy: ## Delete training workload microservices
	@echo -e "$(YELLOW)===> Deleting training workload microservices...$(RESET)"
	kubectl delete -k $(GITOPS_DIR)/apps/training-app --ignore-not-found

SCENARIO ?=

.PHONY: drill-list
drill-list: ## Display catalog of all available troubleshooting drills
	@python3 $(SCRIPTS_DIR)/drill_manager.py --list

.PHONY: drill-inject
drill-inject: ## Inject a specific failure scenario (usage: make drill-inject SCENARIO=<id>)
	@python3 $(SCRIPTS_DIR)/drill_manager.py --inject $(SCENARIO)

.PHONY: drill-verify
drill-verify: ## Verify symptoms of an active scenario (usage: make drill-verify SCENARIO=<id>)
	@python3 $(SCRIPTS_DIR)/drill_manager.py --verify $(SCENARIO)

.PHONY: drill-heal
drill-heal: ## Restore healthy state (usage: make drill-heal SCENARIO=<id> or SCENARIO=all)
	@python3 $(SCRIPTS_DIR)/drill_manager.py --heal $(if $(SCENARIO),$(SCENARIO),all)

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

