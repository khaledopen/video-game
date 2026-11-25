uniform sampler2D u_bend;
in vec2 in_pos;
in vec4 i_rect;   // x, z, demi-largeur, demi-longueur
in vec4 i_col;    // rgb, alpha sombre
in vec2 i_kind;   // type, lacet
out vec2 v_uv; out vec4 v_col; flat out int v_kind; out vec3 v_pos;
void main(){
    v_uv = in_pos; v_col = i_col; v_kind = int(i_kind.x+.5);
    float c = cos(i_kind.y), s = sin(i_kind.y);
    vec2 q = in_pos * i_rect.zw; q = vec2(c*q.x + s*q.y, -s*q.x + c*q.y);
    vec3 w = vec3(i_rect.x + q.x, .02 + .004*i_kind.x, i_rect.y + q.y);
    v_pos = w;
    w.xy += texture(u_bend, vec2((w.z + 30.) / u_track.z, .5)).xy;
    gl_Position = u_vp * vec4(w, 1.);
}