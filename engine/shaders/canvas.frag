#version 330 core
uniform sampler2D u_atlas, u_glow, u_image, u_blur;
uniform vec2 u_size; uniform float u_time;
in vec2 v_p; in vec2 v_half; in vec2 v_uv; in vec2 v_t;
flat in vec4 v_c0; flat in vec4 v_c1; flat in vec4 v_c2; flat in vec4 v_par; flat in int v_kind; flat in vec4 v_par2;
out vec4 frag;
float sdChamfer(vec2 p, vec2 b, float c){          // coins coupes en diagonale
    p = abs(p); vec2 d = p-b;
    float box = length(max(d,0.)) + min(max(d.x,d.y),0.);
    float cut = (p.x+p.y-(b.x+b.y-c))*.70710678;
    return max(box, cut);
}
float sdChamferDiag(vec2 p, vec2 b, float c){      // deux coins opposes seulement
    vec2 q = abs(p); vec2 d = q-b;
    float box = length(max(d,0.)) + min(max(d.x,d.y),0.);
    float cut = (abs(p.x-p.y)-(b.x+b.y-c))*.70710678;
    return max(box, cut);
}
void main(){
    if(v_kind==0 || v_kind==5){                     // panneau (5 = verre depoli)
        // par : coupe, bordure, halo, style (0 tous coins, 1 diagonale, 2 arrondi)
        float d = v_par.w < .5 ? sdChamfer(v_p, v_half, v_par.x) : v_par.w < 1.5 ? sdChamferDiag(v_p, v_half, v_par.x)
                 : (length(max(abs(v_p)-v_half+v_par.x,0.)) + min(max(abs(v_p.x)-v_half.x+v_par.x,abs(v_p.y)-v_half.y+v_par.x),0.) - v_par.x);
        float aa = fwidth(d);
        float inside = smoothstep(aa*.6,-aa*.6,d);
        vec4 f = mix(v_c0, v_c1, clamp(v_par2.w > .5 ? v_t.x : v_t.y,0.,1.));
        vec3 col = f.rgb; float a = f.a;
        if(v_kind==5){
            vec2 su = gl_FragCoord.xy/u_size;
            vec3 b = texture(u_blur, su).rgb; b = b/(1.+b); b = pow(b, vec3(1./2.2))*.85;
            col = mix(b, f.rgb, f.a); a = 1.;
            float sheen = smoothstep(.0,.9,1.-v_t.y)*.055 + .05*smoothstep(.06,.0,abs(v_t.x*.6+v_t.y-.32));
            col += sheen;
        }
        float bw = v_par.y;
        if(bw > 0.){ float e = smoothstep(aa*.6,-aa*.6,abs(d+bw*.5)-bw*.5);
            vec4 bc = v_c2; bc.a *= .55+.45*smoothstep(0.,1.,abs(v_t.x-v_t.y)+.15);
            col = mix(col, bc.rgb, e*bc.a); a = max(a, e*bc.a); }
        a *= inside;
        vec4 o = vec4(col*a, a);
        if(v_par.z > 0.){ float g = exp(-max(d,0.)*3.2/v_par.z)*smoothstep(v_par.z+1.,0.,d)*(1.-inside);
            o += vec4(v_c2.rgb, .25)*g*v_c2.a*.55; }
        frag = o; return;
    }
    if(v_kind==1){                                  // glyphe
        float m = texture(u_atlas, v_uv).r;
        vec4 f = mix(v_c0, v_c1, v_t.y);
        float a = m*f.a; frag = vec4(f.rgb*a, a); return;
    }
    if(v_kind==2){                                  // halo de glyphe (additif)
        float m = texture(u_glow, v_uv).r; frag = vec4(v_c0.rgb*m*v_c0.a, m*v_c0.a*.10); return;
    }
    if(v_kind==3){                                  // arc : par = rayon, epaisseur, a0, a1 ; par2.w = graduations
        float r = length(v_p), ang = atan(v_p.x, -v_p.y);
        float aa = 1.2;
        float d = abs(r - v_par.x) - v_par.y*.5;
        float a = smoothstep(aa,-aa,d);
        float t = (ang - v_par.z)/(v_par.w - v_par.z);
        float ea = aa/max(v_par.x,1.)/max(abs(v_par.w-v_par.z),1e-4);
        a *= smoothstep(-ea,ea,t)*smoothstep(1.+ea,1.-ea,t);
        if(v_par2.w > .5){ float k = fract(t*v_par2.w); float w = fwidth(t*v_par2.w); a *= smoothstep(.06,.06+w*1.5,k)*smoothstep(.94,.94-w*1.5,k); }
        vec4 f = mix(v_c0, v_c1, clamp(t,0.,1.));
        float g = exp(-max(d,0.)*.22)*step(0.,t)*step(t,1.)*.20*v_c2.a;
        frag = vec4(f.rgb*f.a*a + f.rgb*g*f.a, f.a*a); return;
    }
    if(v_kind==4){                                  // image RGBA
        vec4 t = texture(u_image, v_uv); t.a *= v_c0.a; frag = vec4(t.rgb*v_c0.rgb*t.a, t.a);
        if(v_par.w > .5){ float d = sdChamfer(v_p, v_half, v_par.x); frag *= smoothstep(1.,-1.,d); }
        return;
    }
    if(v_kind==6){                                  // halo radial
        float r = length(v_t*2.-1.); float a = pow(max(1.-r,0.),2.); frag = vec4(v_c0.rgb*a*v_c0.a, 0.); return;
    }
    if(v_kind==7){                                  // triangle oriente vers la droite
        vec2 q = v_p/v_half; float d = max(abs(q.y) - (1.-q.x)*.5, -q.x-1.); float aa = fwidth(d);
        float a = smoothstep(aa,-aa,d)*v_c0.a; frag = vec4(v_c0.rgb*a,a); return;
    }
    if(v_kind==8){                                  // barre segmentee : par.x = remplissage, par.y = segments, par.z = coupe
        float d = sdChamferDiag(v_p, v_half, v_par.z); float aa = fwidth(d);
        float in_s = smoothstep(aa*.6,-aa*.6,d);
        float t = v_t.x, k = fract((t - (v_t.y-.5)*v_half.y/v_half.x*.8)*v_par.y), w = fwidth(t*v_par.y);
        float seg = v_par.y > .5 ? smoothstep(.05,.05+w*1.5,k)*smoothstep(.95,.95-w*1.5,k) : 1.;
        float on = smoothstep(v_par.x+.002, v_par.x-.002, t);
        vec4 f = mix(v_c0, v_c1, t); vec4 o = mix(v_c2, f, on);
        float lead = on*smoothstep(.05,.0,v_par.x-t)*.6;
        o.rgb += lead; float a = o.a*in_s*mix(.25,1.,seg);
        frag = vec4(o.rgb*a,a); return;
    }
    frag = vec4(v_c0.rgb*v_c0.a, v_c0.a);
}