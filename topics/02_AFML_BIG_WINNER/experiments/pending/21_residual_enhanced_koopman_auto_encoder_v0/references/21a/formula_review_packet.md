# EP21A Formula Review Packet

- paper_sha256: `1041d8693c5ef80fcafc613d77f09bf3ec2a2df673f468785255da27d7d9a472`
- page_count: `5`
- source_manifest_sha256: `f8f2a2d160c52b10a9b8c3c9f5ad8961ed23fc7b69951e420ab78061a4e9b2a0`

Human review must approve or reject the complete required formula set; partial approval cannot pass.

## P01_INPUT_RETURN_AND_FEATURE_SEQUENCES

- Page: `1`
- Anchor: `paragraph beginning 'Given a collection of S financial assets'`
- Paper canonical: `X_i=[x_i,1,...,x_i,T], y_i=[y_i,1,...,y_i,T]; y_hat_i,t+1=M(X_i^1:t,y_i^1:t)`
- Project mapping: `x_source and y_source are trailing sequences ending at decision close t`
- Gap/adaptation: Paper input semantics retained; project fixes PIT timing separately.

## P02_DUAL_LSTM_ENCODERS

- Page: `2`
- Anchor: `Equations (1)-(6)`
- Paper canonical: `H_y=LSTM_y(y_1:T-1); H_y_plus=LSTM_y(y_2:T); H_x=LSTM_x(x_1:T-1); H_x_plus=LSTM_x(x_2:T)`
- Project mapping: `shared dual LSTM encoders process source and shifted teacher sequences`
- Gap/adaptation: The paper-disclosed overlapping segments are retained with project-explicit tensor indexing.

## P03_SIGMOID_FEATURE_GATE

- Page: `2`
- Anchor: `Equations (7)-(8) and paragraph after Equation (10)`
- Paper canonical: `G=GateNet(H_x); G_plus=GateNet(H_x_plus), where GateNet is an MLP followed by sigmoid`
- Project mapping: `G=sigmoid(Linear(H_x)); the shared GateNet is applied once per source/teacher encoding`
- Gap/adaptation: Paper leaves MLP depth open; project freezes a single affine layer plus one sigmoid.

## P04_LATENT_FUSION_Z_AND_Z_PLUS

- Page: `2`
- Anchor: `Equations (9)-(10)`
- Paper canonical: `Z=H_y odot G+H_x odot (1-G); Z_plus=H_y_plus odot G_plus+H_x_plus odot (1-G_plus)`
- Project mapping: `Z_source and train-only Z_teacher_shifted use the same elementwise gated fusion`
- Gap/adaptation: Project names source/teacher roles explicitly to prevent inference leakage.

## P05_OPERATOR_CODEBOOK

- Page: `2`
- Anchor: `paragraph containing 'codebook K={K1,K2,...,KN}' before Equation (11)`
- Paper canonical: `K_codebook={K_1,K_2,...,K_N}`
- Project mapping: `four learnable 64x64 Koopman matrices form the primary codebook`
- Gap/adaptation: N and latent dimension are project choices because the paper does not disclose them.

## P06_GUMBEL_SOFTMAX_SELECTOR

- Page: `2`
- Anchor: `Equations (11)-(13)`
- Paper canonical: `a=LeakyReLU(W[Z,H_y]^h); alpha_i=exp((a_i+epsilon_i)/tau)/sum_j exp((a_j+epsilon_j)/tau)`
- Project mapping: `state-conditioned LeakyReLU selector with soft Gumbel-Softmax in train and hard argmax in inference`
- Gap/adaptation: Temperature schedule and hard-inference rule are project-frozen where the paper is silent.

## P07_SELECTED_KOOPMAN_PROPAGATION

- Page: `2`
- Anchor: `Equation (14), continuing with Equation (15) on PDF page 3`
- Paper canonical: `K_s=sum_i alpha_i K_i; Z_hat_plus=K_s Z`
- Project mapping: `K_selected[b,t]=sum_i alpha[b,t,i]K_i; Z_hat_shifted=einsum(K_selected,Z_source)`
- Gap/adaptation: Project makes batch/time axes and matrix multiplication explicit.

## P08_LATENT_RESIDUAL

- Page: `3`
- Anchor: `first paragraph, sentence 'Let the residual be R=Z+ - Z_hat+'`
- Paper canonical: `R=Z_plus-Z_hat_plus`
- Project mapping: `residual_target=Z_teacher_shifted-Z_hat_shifted is train-only`
- Gap/adaptation: Project explicitly isolates the true shifted latent from inference ancestors.

## P09_CONDITIONAL_DDPM_FORWARD_NOISE

- Page: `3`
- Anchor: `Equation (16)`
- Paper canonical: `x_t=sqrt(alpha_bar_t)R+sqrt(1-alpha_bar_t)epsilon, epsilon~N(0,I)`
- Project mapping: `x_s=sqrt(alpha_bar_s)residual_target+sqrt(1-alpha_bar_s)epsilon`
- Gap/adaptation: Variable s is used for diffusion time to avoid collision with market date t.

## P10_DDPM_EPSILON_LOSS

- Page: `3`
- Anchor: `Equation (17)`
- Paper canonical: `L_diff=E_t,epsilon ||epsilon_theta(x_t,t,Z)-epsilon||_2^2`
- Project mapping: `L_diff=MeanValid((epsilon_theta(x_s,s,Z_source)-epsilon)^2)`
- Gap/adaptation: Project freezes finite-cell mean reduction axes.

## P11_REVERSE_RESIDUAL_SAMPLE

- Page: `3`
- Anchor: `Equations (18)-(20)`
- Paper canonical: `mu_theta=(x_t-(1-alpha_t)/sqrt(1-alpha_bar_t)*epsilon_theta)/sqrt(alpha_t); sigma_t^2=((1-alpha_bar_{t-1})/(1-alpha_bar_t))*beta_t; x_{t-1}=mu_theta+sigma_t xi`
- Project mapping: `20-step DDPM reverse chain with the paper equations and independently keyed draw noise`
- Gap/adaptation: Step count and seed-key contract are project choices.

## P12_RESIDUAL_ENHANCED_LATENT

- Page: `3`
- Anchor: `Equation (21)`
- Paper canonical: `Z_tilde_plus=Z_hat_plus+R_hat`
- Project mapping: `Z_tilde_shifted=Z_hat_shifted+R_hat for train reconstruction and inference draws`
- Gap/adaptation: Paper correction rule retained with explicit train/inference roles.

## P13_RETURN_DECODER

- Page: `3`
- Anchor: `Equations (22)-(23) and Equation (27)`
- Paper canonical: `y_hat_1:T-1=Decoder(Z); y_hat_2:T=Decoder(Z_tilde_plus); y_hat_2:t+1=Decoder(Z_plus)`
- Project mapping: `shared scalar decoder reconstructs source/shifted sequences; score is the last shifted output`
- Gap/adaptation: Project resolves the Equation (27) notation against the preceding corrected-latent definition.

## P14_L_REC_L_KOOP_L_DIFF

- Page: `3`
- Anchor: `Equations (28)-(31)`
- Paper canonical: `L_total=L_rec+L_koop+L_diff; L_rec=MSE(y_hat_1:T-1,y_1:T-1)+MSE(y_hat_2:T,y_2:T); L_koop=MSE(Z_hat_plus,Z_plus)`
- Project mapping: `L_total=L_rec+L_koop+L_diff with L_forecast included exactly once inside L_rec`
- Gap/adaptation: Paper top-level weights are retained; project freezes valid-cell reductions and forecast counting.

## P15_T10_LOOKBACK

- Page: `3`
- Anchor: `sentence 'The lookback window length T is set to 10 trading days'`
- Paper canonical: `T=10 trading days`
- Project mapping: `lookback_T=10 exchange sessions ending at decision close t`
- Gap/adaptation: Paper value retained and PIT calendar semantics made explicit.

## P16_RANKIC_AND_RANKICIR

- Page: `3`
- Anchor: `final metric-definition sentence before Section 4.2`
- Paper canonical: `RankIC_t=Spearman(rank(r_hat_t),rank(r_t)); printed RankICIR denominator is mean(RankIC_t)`
- Project mapping: `RankIC=float64 Pearson of average ranks; RankICIR=mean(RankIC_t)/std(RankIC_t,ddof=1)`
- Gap/adaptation: The printed RankICIR denominator appears inconsistent; project registers the conventional standard-deviation denominator and cannot claim exact metric replication.

## P17_TOPK30_DIAGNOSTIC

- Page: `4`
- Anchor: `paragraph containing 'In our experiments, K=30' and Figure 4`
- Paper canonical: `rank candidates by predicted score and hold TopK with K=30`
- Project mapping: `TopK=30 gross close proxy and distinct next-open executable ledger under EP19/EP20 rules`
- Gap/adaptation: Paper does not disclose local PIT timing/cost details; executable economics are a project adaptation.

## A01_FULL_T_SHIFTED_SEQUENCE_INDEXING

- Page: `2`
- Anchor: `Equations (1)-(10), overlapping source/shifted segments`
- Paper canonical: `paper uses y_1:T-1 versus y_2:T and x_1:T-1 versus x_2:T`
- Project mapping: `source_dates=[t-T+1..t]; teacher_shifted_dates=[t-T+2..t+1], each with T transitions`
- Gap/adaptation: Project extends the overlapping construction to an explicit T-transition forecasting contract.

## A02_FINAL_STEP_SCORE_INDEX

- Page: `3`
- Anchor: `sentence after Equation (27): estimated return is the last reconstructed element`
- Paper canonical: `y_hat_t+1 is the last element of reconstructed y_hat_2:t+1`
- Project mapping: `score_next=decoded_shifted[:,-1]`
- Gap/adaptation: Project fixes the tensor index and scalar shape.

## A03_MEAN_LOSS_REDUCTION_AXES

- Page: `3`
- Anchor: `Equations (28)-(31), MSE reductions not further disclosed`
- Paper canonical: `paper specifies MSE objectives without batch/time/latent reduction order`
- Project mapping: `MeanValid means latent-element mean followed by valid batch/time-cell mean`
- Gap/adaptation: Unique reduction axes are needed for reproducible loss scale and batch-duplication invariance.

## A04_TEACHER_GRADIENT_AND_INFERENCE_ISOLATION

- Page: `2`
- Anchor: `page 2 sentence 'At inference, only past returns and features are used'; page 3 residual conditioning on Z`
- Paper canonical: `inference uses only past returns/features; diffusion corrector is conditioned on current latent Z`
- Project mapping: `teacher tensors only construct train targets/noising and never enter selector, condition, or inference-score ancestors`
- Gap/adaptation: Project freezes the only leakage-safe graph consistent with the paper prose.

## A05_EIGHT_DRAW_POINT_PREDICTION_MEAN

- Page: `3`
- Anchor: `Equations (18)-(21), one residual sample described; draw aggregation undisclosed`
- Paper canonical: `reverse diffusion maps x_0 to a residual sample R_hat`
- Project mapping: `point score is the arithmetic mean of eight independently keyed reverse-diffusion draws`
- Gap/adaptation: Draw count and point aggregation are undisclosed project choices.

## A06_PROJECT_PIT_UNIVERSE_AND_TIMING

- Page: `3`
- Anchor: `CSI300/S&P500, 2010-2020 and Alpha158 setup paragraph; no PIT membership timing disclosed`
- Paper canonical: `paper evaluates fixed named universes and does not disclose point-in-time membership/execution timing`
- Project mapping: `membership at close t defines U_t_membership; usable_trade_date is exactly the next exchange session; U_t_decision is outcome-independent`
- Gap/adaptation: Local PIT universe and execution timing are necessary project adaptations and prohibit a CSI300 exact-replication claim.
