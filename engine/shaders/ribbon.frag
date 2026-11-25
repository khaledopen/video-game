in vec4 v_col; in float v_u; out vec4 frag;
void main(){ float a = pow(1.-abs(v_u),1.5); frag = vec4(v_col.rgb*v_col.a*(a + .8*smoothstep(.35,.0,abs(v_u))), 0.); }