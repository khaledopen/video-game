uniform sampler2D u_bend;
in vec3 in_pos; in vec4 in_col; in float in_u;
out vec4 v_col; out float v_u;
void main(){
    vec3 w = in_pos; w.xy += texture(u_bend, vec2((w.z + 30.) / u_track.z, .5)).xy;
    v_col = in_col; v_u = in_u;
    gl_Position = u_vp * vec4(w,1.);
}